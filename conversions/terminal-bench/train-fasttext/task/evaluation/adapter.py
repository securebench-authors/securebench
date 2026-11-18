"""train-fasttext adapter: predict one label per review with /app/model.bin.

Upstream's verifier calls `fasttext.load_model("/app/model.bin")` and then
`model.predict(text)[0][0]` for every review, with the `fasttext-wheel==0.9.2`
package it installs from the network at grading time. Evaluation environments
have no network, so this file reimplements exactly that path of fastText 0.9.2
(`FastText::loadModel`, `Dictionary::getLine`, `Model::predict` and the four
losses), including its float32 arithmetic, so that it predicts the same label
as the native library for every review.

It runs on the baseline's own Python 3.13 and NumPy, which live outside the
capture scope, so a candidate cannot change them. NumPy is used only for
elementwise float32 additions and products and for `np.add.accumulate`, which
adds strictly in sequence. Together these reproduce fastText's sequential
float32 loops bit for bit. `np.add.reduce`, `dot` and `sum` reorder additions
and are never used.

Assertion-free: it reports the size of the model file and, for each review,
which label the model predicted, and holds no expected label or size limit.
Where fastText would raise an error, the adapter reports `unable`; where
fastText would read out of bounds or divide by zero, it reports `unable` too
instead of guessing.
"""

import ctypes
import gzip
import json
import math
import struct
import sys
from array import array
from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

MODEL = "/app/model.bin"
REVIEWS = "/.securebench/evaluation/reviews.txt.gz"
# A protocol bound on what the adapter loads; upstream accepts only models under 150 MiB.
MAX_MODEL_BYTES = 512 << 20
MAX_LABEL_BYTES = 4096

MAGIC = 793712314
VERSION = 12
SUPERVISED = 3
HS, NS, SOFTMAX, OVA = 1, 2, 3, 4
EOS = b"</s>"
LABEL_PREFIX = b"__label__"
KSUB = 256
MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF
INT32_MAX = (1 << 31) - 1
NGRAM_MULTIPLIER = 116049371

type Floats = NDArray[np.float32]

_scratch = array("f", [0.0])


def f32(value: float) -> float:
    """Round a double to float32, as a C++ `real` assignment does."""
    _scratch[0] = value
    return _scratch[0]


def int64(value: int) -> int:
    """Wrap to a signed 64-bit integer, as fastText's int64_t sums do."""
    return (value + (1 << 63)) % (1 << 64) - (1 << 63)


def _expf() -> Callable[[float], float]:
    # fastText calls glibc's expf, which is not always correctly rounded, so the
    # adapter calls the same function rather than rounding a double exp.
    libm = ctypes.CDLL("libm.so.6")
    function = libm.expf
    function.restype = ctypes.c_float
    function.argtypes = [ctypes.c_float]
    return function


expf = _expf()


def std_log(value: float) -> float:
    """fastText's `std_log`: log(x + 1e-5) in double, returned as float32."""
    return f32(math.log(value + 1e-5))


def running_sum(rows: Floats) -> Floats:
    """Column sums of `rows`, added one row at a time in float32 from +0, as fastText's loops do."""
    total = np.zeros((1, rows.shape[1]), dtype=np.float32)
    if rows.shape[0] == 0:
        return total[0]
    return np.add.accumulate(np.concatenate((total, rows)), axis=0, dtype=np.float32)[-1]


def dot(row: Floats, hidden: Floats) -> float:
    """Sequential float32 dot product, as fastText's dotRow and mulcode compute it."""
    if row.shape[0] == 0:
        return 0.0
    products = np.multiply(row, hidden[: row.shape[0]], dtype=np.float32)
    return float(np.add.accumulate(products, dtype=np.float32)[-1])


class Unable(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def malformed(message: str) -> Unable:
    return Unable("malformed-model", message)


class Reader:
    """Bounded little-endian reads; a short read is a malformed model, never zero fill."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.position = 0

    def take(self, count: int) -> bytes:
        if count < 0 or self.position + count > len(self.data):
            raise malformed(f"file ends before byte {self.position + count}")
        chunk = self.data[self.position : self.position + count]
        self.position += count
        return chunk

    def unpack(self, fmt: str) -> int | float:
        return struct.unpack("<" + fmt, self.take(struct.calcsize(fmt)))[0]

    def i32(self) -> int:
        return int(self.unpack("i"))

    def i64(self) -> int:
        return int(self.unpack("q"))

    def flag(self) -> bool:
        value = self.take(1)[0]
        if value not in (0, 1):
            raise malformed(f"boolean byte {value}")
        return value == 1

    def string(self) -> bytes:
        end = self.data.find(b"\0", self.position)
        if end < 0:
            raise malformed("unterminated dictionary entry")
        word = self.data[self.position : end]
        self.position = end + 1
        return word

    def floats(self, count: int) -> Floats:
        if count < 0 or self.position + 4 * count > len(self.data):
            raise malformed(f"file ends before byte {self.position + 4 * count}")
        values = np.frombuffer(self.data, dtype="<f4", count=count, offset=self.position)
        self.position += 4 * count
        return values.astype(np.float32, copy=False)

    def codes(self, count: int) -> NDArray[np.uint8]:
        if count < 0 or self.position + count > len(self.data):
            raise malformed(f"file ends before byte {self.position + count}")
        values = np.frombuffer(self.data, dtype=np.uint8, count=count, offset=self.position)
        self.position += count
        return values


class Quantizer:
    """fastText's ProductQuantizer, as loaded."""

    def __init__(self, reader: Reader) -> None:
        self.dim = reader.i32()
        self.nsubq = reader.i32()
        self.dsub = reader.i32()
        self.lastdsub = reader.i32()
        if self.dim < 0 or min(self.nsubq, self.dsub, self.lastdsub) < 1:
            raise malformed("product quantizer with a non-positive size")
        # Every centroid read of get_centroids stays inside centroids_ exactly when
        # the code length is at most dim; fastText checks nothing.
        self.length = (self.nsubq - 1) * self.dsub + self.lastdsub
        if self.length > self.dim:
            raise malformed("product quantizer reads past its centroids")
        centroids = reader.floats(self.dim * KSUB)
        self.tables: list[Floats] = []
        for m in range(self.nsubq):
            width = self.lastdsub if m == self.nsubq - 1 else self.dsub
            start = m * KSUB * self.dsub
            self.tables.append(centroids[start : start + KSUB * width].reshape(KSUB, width))

    def decode(self, codes: NDArray[np.uint8]) -> Floats:
        """The centroid rows for a (rows, nsubq) code matrix, concatenated per row."""
        return np.concatenate([table[codes[:, m]] for m, table in enumerate(self.tables)], axis=1)


class Dense:
    def __init__(self, reader: Reader) -> None:
        self.rows = reader.i64()
        self.cols = reader.i64()
        if self.rows < 0 or self.cols < 0:
            raise malformed("matrix with a negative size")
        self.data = reader.floats(self.rows * self.cols).reshape(self.rows, self.cols)

    def sum_rows(self, ids: list[int]) -> Floats:
        return running_sum(self.data[ids])

    def dot_row(self, hidden: Floats, i: int) -> float:
        return dot(self.data[i], hidden)


class Quantized:
    def __init__(self, reader: Reader) -> None:
        self.qnorm = reader.flag()
        self.rows = reader.i64()
        self.cols = reader.i64()
        codesize = reader.i32()
        if self.rows < 0 or self.cols < 0 or codesize < 0:
            raise malformed("quantized matrix with a negative size")
        codes = reader.codes(codesize)
        self.pq = Quantizer(reader)
        if self.pq.length > self.cols or codesize < self.rows * self.pq.nsubq:
            raise malformed("quantized matrix does not match its quantizer")
        self.codes = codes[: self.rows * self.pq.nsubq].reshape(self.rows, self.pq.nsubq)
        self.norms: Floats | None = None
        if self.qnorm:
            norm_codes = reader.codes(self.rows)
            npq = Quantizer(reader)
            # QuantMatrix reads npq_->get_centroids(0, code)[0].
            self.norms = npq.tables[0][norm_codes, 0]

    def rows_of(self, ids: list[int]) -> Floats:
        """ProductQuantizer::addcode's terms: each row's centroids times its norm."""
        rows = self.pq.decode(self.codes[ids])
        if self.norms is not None:
            rows = np.multiply(self.norms[ids][:, None], rows, dtype=np.float32)
        return rows

    def sum_rows(self, ids: list[int]) -> Floats:
        total = np.zeros(self.cols, dtype=np.float32)
        total[: self.pq.length] = running_sum(self.rows_of(ids))
        return total

    def dot_row(self, hidden: Floats, i: int) -> float:
        norm = 1.0 if self.norms is None else float(self.norms[i])
        return f32(dot(self.pq.decode(self.codes[i : i + 1])[0], hidden) * norm)


type Matrix = Dense | Quantized


def fnv(data: bytes) -> int:
    """Dictionary::hash: 32-bit FNV-1a over the bytes as signed chars."""
    h = 2166136261
    for byte in data:
        h = ((h ^ (byte if byte < 128 else byte | 0xFFFFFF00)) * 16777619) & MASK32
    return h


class Model:
    def __init__(self, data: bytes) -> None:
        reader = Reader(data)
        if reader.i32() != MAGIC:
            raise Unable("wrong-format", "not a fastText model (magic number)")
        version = reader.i32()
        if version > VERSION:
            raise Unable("wrong-format", f"fastText model version {version}")
        (dim, _ws, _epoch, _min_count, _neg, word_ngrams, loss, model, bucket, minn, maxn) = (
            reader.i32() for _ in range(11)
        )
        reader.i32()
        reader.take(8)
        if version == 11 and model == SUPERVISED:
            maxn = 0
        if model != SUPERVISED:
            raise Unable("not-supervised", "Model needs to be supervised for prediction!")
        if loss not in (HS, NS, SOFTMAX, OVA):
            raise Unable("unknown-loss", f"Unknown loss {loss}")
        if dim < 0 or bucket < 0:
            raise malformed(f"dim {dim}, bucket {bucket}")
        self.dim, self.loss, self.bucket = dim, loss, bucket
        self.word_ngrams, self.maxn = word_ngrams, maxn
        # computeSubwords compares a size_t n with these int32 values, so a
        # negative maxn sets no upper bound and a negative minn admits no n-gram.
        self.minn_unsigned, self.maxn_unsigned = minn & MASK64, maxn & MASK64

        size, self.nwords, nlabels = reader.i32(), reader.i32(), reader.i32()
        reader.i64()
        self.pruneidx_size = reader.i64()
        if self.nwords < 0 or nlabels < 1 or size != self.nwords + nlabels:
            raise malformed(f"dictionary of {size} entries, {self.nwords} words, {nlabels} labels")
        self.vocabulary: dict[bytes, int] = {}
        self.labels: list[bytes] = []
        self.label_counts: list[int] = []
        for i in range(size):
            word = reader.string()
            count = reader.i64()
            kind = reader.take(1)[0]
            # Dictionary::threshold sorts words before labels; anything else is not a saved model.
            if kind != (0 if i < self.nwords else 1):
                raise malformed(f"dictionary entry {i} has type {kind}")
            self.vocabulary[word] = i
            if i >= self.nwords:
                self.labels.append(word)
                self.label_counts.append(count)
        self.pruneidx: dict[int, int] = {}
        for _ in range(max(self.pruneidx_size, 0)):
            first = reader.i32()
            self.pruneidx[first] = reader.i32()

        quant_input = reader.flag()
        self.input: Matrix = Quantized(reader) if quant_input else Dense(reader)
        if not quant_input and self.pruneidx_size >= 0:
            raise Unable("invalid-model", "Invalid model file (pruned dictionary, dense input)")
        qout = reader.flag()
        self.output: Matrix = Quantized(reader) if quant_input and qout else Dense(reader)
        if self.input.cols != dim or self.output.cols != dim:
            raise malformed("matrix width differs from dim")
        # Softmax and the binary losses read one output row per label; the tree, one per inner node.
        if self.output.rows < (nlabels - 1 if self.loss == HS else nlabels):
            raise malformed("output matrix has fewer rows than the loss reads")
        if self.loss == HS:
            self.tree = self._tree()
        self.sigmoid = self._sigmoid_table()
        self.log_threshold = std_log(0.0)
        self.tokens: dict[bytes, tuple[tuple[int, ...], int] | None] = {}

    # Dictionary::getLine and its helpers.

    def _modulo(self, value: int) -> int:
        if self.bucket == 0:
            raise Unable("division-by-zero", "fastText would divide a hash by bucket 0")
        return value % self.bucket

    def _push_hash(self, ids: list[int], bucket_id: int) -> None:
        if self.pruneidx_size == 0 or bucket_id < 0:
            return
        if self.pruneidx_size > 0:
            if bucket_id not in self.pruneidx:
                return
            bucket_id = self.pruneidx[bucket_id]
        ids.append(self.nwords + bucket_id)

    def _subwords(self, word: bytes, ids: list[int]) -> None:
        """Dictionary::computeSubwords: character n-grams of `<word>`, by UTF-8 character."""
        length = len(word)
        for i in range(length):
            if word[i] & 0xC0 == 0x80:
                continue
            j, n = i, 1
            while j < length and n <= self.maxn_unsigned:
                j += 1
                while j < length and word[j] & 0xC0 == 0x80:
                    j += 1
                if n >= self.minn_unsigned and not (n == 1 and (i == 0 or j == length)):
                    self._push_hash(ids, self._modulo(fnv(word[i:j])))
                n += 1

    def _token(self, token: bytes) -> tuple[tuple[int, ...], int] | None:
        """Input rows and the int32 hash of a word token; None for a label token."""
        known = self.tokens.get(token, -1)
        if known != -1:
            return known
        wid = self.vocabulary.get(token)
        result: tuple[tuple[int, ...], int] | None
        is_label = token.startswith(LABEL_PREFIX) if wid is None else wid >= self.nwords
        if is_label:
            result = None
        else:
            ids: list[int] = []
            if wid is None:
                if token != EOS:
                    self._subwords(b"<" + token + b">", ids)
            elif self.maxn <= 0:
                ids.append(wid)
            else:
                ids.append(wid)
                if token != EOS:
                    self._subwords(b"<" + token + b">", ids)
            h = fnv(token)
            result = (tuple(ids), h - (1 << 32) if h >= 1 << 31 else h)
        self.tokens[token] = result
        return result

    def features(self, text: bytes) -> list[int]:
        # predict() appends "\n"; readWord splits on these bytes and turns the
        # final newline into EOS, and getLine stops at the first EOS token.
        tokens = text.replace(b"\0", b" ").split()
        tokens.append(EOS)
        ids: list[int] = []
        hashes: list[int] = []
        for token in tokens:
            entry = self._token(token)
            if entry is not None:
                ids.extend(entry[0])
                hashes.append(entry[1])
            if token == EOS:
                break
        # addWordNgrams computes `i + wordNgrams` in int32 whenever i + 1 < hashes.size(),
        # so a wordNgrams near 2^31 overflows, which is undefined behaviour.
        if len(hashes) >= 2 and len(hashes) - 2 + self.word_ngrams > INT32_MAX:
            raise Unable("integer-overflow", f"wordNgrams {self.word_ngrams} overflows int32")
        for i in range(len(hashes)):
            h = hashes[i] & MASK64
            for j in range(i + 1, min(len(hashes), i + self.word_ngrams)):
                h = (h * NGRAM_MULTIPLIER + hashes[j]) & MASK64
                self._push_hash(ids, self._modulo(h))
        return ids

    # Model::predict and the losses, for k = 1 and threshold 0.

    def _hidden(self, ids: list[int]) -> Floats:
        for i in ids:
            if not 0 <= i < self.input.rows:
                raise malformed(f"input row {i} out of range")
        hidden = self.input.sum_rows(ids)
        scale = np.float32(f32(1.0 / len(ids)))
        return np.multiply(hidden, scale, dtype=np.float32)

    def _dot(self, hidden: Floats, i: int) -> float:
        value = self.output.dot_row(hidden, i)
        if not math.isfinite(value):
            raise Unable("non-finite", f"output row {i} gives {value}")
        return value

    def predict(self, text: bytes) -> int | None:
        """The label index fastText predicts, or None when it predicts nothing."""
        ids = self.features(text)
        if not ids:
            return None
        hidden = self._hidden(ids)
        if self.loss == HS:
            return self._predict_tree(hidden)
        if self.loss == SOFTMAX:
            outputs = self._softmax(hidden)
        else:
            outputs = [self._sigmoid(self._dot(hidden, i)) for i in range(len(self.labels))]
        best: tuple[float, int] | None = None
        for i, value in enumerate(outputs):
            if value < 0.0:
                continue
            score = std_log(value)
            # Loss::findKBest with k = 1: a later index wins a tie.
            if best is not None and score < best[0]:
                continue
            best = (score, i)
        return None if best is None else best[1]

    def _softmax(self, hidden: Floats) -> list[float]:
        outputs = [self._dot(hidden, i) for i in range(len(self.labels))]
        top = outputs[0]
        for value in outputs:
            top = top if value < top else value
        total = 0.0
        for i, value in enumerate(outputs):
            outputs[i] = f32(math.exp(f32(value - top)))
            total = f32(total + outputs[i])
        return [f32(value / total) for value in outputs]

    def _sigmoid_table(self) -> list[float]:
        table: list[float] = []
        for i in range(513):
            x = f32(i * 16 / 512 - 8)
            table.append(f32(1.0 / (1.0 + expf(-x))))
        return table

    def _sigmoid(self, x: float) -> float:
        if x < -8:
            return 0.0
        if x > 8:
            return 1.0
        return self.sigmoid[int(f32(x + 8) * 512 / 8 / 2)]

    def _tree(self) -> list[tuple[int, int]]:
        """HierarchicalSoftmaxLoss::buildTree: (left, right) children of every node."""
        osz = len(self.labels)
        counts = [*self.label_counts, *([10**15] * (osz - 1))]
        children = [(-1, -1)] * (2 * osz - 1)
        leaf, node = osz - 1, osz
        for i in range(osz, 2 * osz - 1):
            pair: list[int] = []
            for _ in range(2):
                # Counts at or above the 1e15 placeholder make fastText pick a node it has
                # not built yet, or read past the tree; it then loops without end.
                if node >= i and not (leaf >= 0 and counts[leaf] < counts[node]):
                    raise malformed("label counts do not build a tree")
                if leaf >= 0 and counts[leaf] < counts[node]:
                    pair.append(leaf)
                    leaf -= 1
                else:
                    pair.append(node)
                    node += 1
            children[i] = (pair[0], pair[1])
            counts[i] = int64(counts[pair[0]] + counts[pair[1]])
        return children

    def _predict_tree(self, hidden: Floats) -> int | None:
        osz = len(self.labels)
        best: tuple[float, int] | None = None
        # HierarchicalSoftmaxLoss::dfs, with an explicit stack: zero or negative label
        # counts build a chain as deep as the number of labels, beyond Python's
        # recursion limit. The right child is pushed first, so the left subtree is
        # searched first and the right child is pruned against its result, as natively.
        stack = [(2 * osz - 2, 0.0)]
        while stack:
            node, score = stack.pop()
            if score < self.log_threshold:
                continue
            if best is not None and score < best[0]:
                continue
            left, right = self.tree[node]
            if left == -1 and right == -1:
                best = (score, node)
                continue
            f = self._dot(hidden, node - osz)
            f = f32(1.0 / f32(1.0 + expf(-f)))
            stack.append((right, f32(score + std_log(f))))
            stack.append((left, f32(score + std_log(f32(1.0 - f)))))
        return None if best is None else best[1]


def observe(expected_reviews: int) -> dict[str, object]:
    with gzip.open(REVIEWS, "rb") as handle:
        texts = handle.read().split(b"\n")
    if texts[-1] != b"" or len(texts) - 1 != expected_reviews:
        raise Unable("reviews", f"{len(texts) - 1} reviews, the challenge says {expected_reviews}")
    try:
        with open(MODEL, "rb") as handle:
            data = handle.read(MAX_MODEL_BYTES + 1)
    except FileNotFoundError:
        raise Unable("model-missing", f"{MODEL} does not exist") from None
    except OSError as error:
        raise Unable("model-unreadable", str(error)) from None
    if len(data) > MAX_MODEL_BYTES:
        raise Unable("model-too-large", f"{MODEL} is larger than {MAX_MODEL_BYTES} bytes")
    model_bytes = len(data)
    model = Model(data)
    # Labels are reported once each, by name, as upstream compares names.
    index: dict[bytes, int] = {}
    labels: list[str] = []
    predictions: list[int] = []
    for text in texts[:-1]:
        label = model.predict(text)
        if label is None:
            predictions.append(-1)
            continue
        word = model.labels[label]
        if word not in index:
            try:
                name = word.decode("utf-8")
            except UnicodeDecodeError:
                raise Unable("label-not-utf8", f"label {label} is not UTF-8") from None
            if len(word) > MAX_LABEL_BYTES:
                raise Unable("label-too-long", f"label {label} is longer than {MAX_LABEL_BYTES}")
            index[word] = len(labels)
            labels.append(name)
        predictions.append(index[word])
    return {"model_bytes": model_bytes, "labels": labels, "predictions": predictions}


def main() -> int:
    challenge = json.loads(sys.stdin.buffer.read())
    try:
        response: dict[str, object] = {"observation": observe(challenge["reviews"])}
    except Unable as unable:
        response = {"unable": {"code": unable.code, "message": unable.message[:4096]}}
    sys.stdout.write(json.dumps(response))
    return 0


if __name__ == "__main__":
    sys.exit(main())
