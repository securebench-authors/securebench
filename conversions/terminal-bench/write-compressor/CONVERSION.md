# write-compressor

Upstream: terminal-bench@2fd12b88aafdd04a52c298e3940bcb189f9766d6/write-compressor

## How the pack grades

The agent must leave `/app/data.comp`, at most 2500 bytes, such that upstream's
decompressor turns it into `data.txt` exactly. Upstream's `tests/test_outputs.py`
has three tests; each first restores `/app/decomp.c` and `/app/data.txt` from the
test directory and compiles `gcc -o decomp2 decomp.c` in `/app`.

| Upstream test | Check | How |
|---|---|---|
| `test_compressed_file_exists` | `data-comp` (artifact) | `/app/data.comp` must be a regular file. |
| `test_compression_size` (`st_size <= 2500`) | `data-comp` (artifact) | The file is declared with `max_bytes = 2500`; the framework reports a larger one as `too_large`, and the Oracle also checks the captured size against 2500. Binary content is reported as `unparsable`, which the Oracle accepts like `present`: only the size matters. |
| `test_decompression_produces_original` | `decompress` (protocol, one case) | `evaluation/adapter.py` copies `evaluation/decomp.c` (upstream's `tests/original-decomp.c`, byte for byte) into a fresh temporary directory, compiles it with `/usr/bin/gcc -o decomp2 decomp.c` exactly as the test does, runs it with `/app/data.comp` on standard input, and reports the exit status, the output length and the first 64 KiB of output in base64. The Oracle requires exit status 0 and output equal to `hidden/data.txt` (upstream's `tests/original-data.txt`, byte for byte) after the same decoding the test applies (below). |

Neither check reads anything the candidate can change other than
`/app/data.comp` itself: the size comes from the captured file, the
decompressor source from `evaluation/`, the compiler from outside the scope, and
the expected text from `hidden/`. The adapter runs under `python3 -I`, so Python
modules the candidate leaves in `/app` (the working directory) are not imported.

### Matching the test's comparison

The test runs `subprocess.run(..., shell=True, capture_output=True, text=True)`
and compares `result.stdout` with `Path("/app/data.txt").read_text()`. Both sides
are decoded as UTF-8 (strict: output that is not valid UTF-8 raises in the test
and fails it) and pass through universal newline translation, which turns
`\r\n` and lone `\r` into `\n`. The Oracle does the same: it decodes the output
with `bytes.decode("utf-8")`, which raises on invalid input, and applies
`replace("\r\n", "\n").replace("\r", "\n")` to both texts, which is what
`subprocess` does in text mode. `mutant-crlf` and `mutant-cr` (accepted by this
translation) and `mutant-cp1252` (rejected by the strict decode) check that the
two graders agree.

The adapter reports at most 65,536 bytes of output and the full length. Any
longer output cannot match: `data.txt` is 4,868 bytes, and even after newline
translation, output of more than 65,536 bytes decodes to more than 4,868
characters. The Oracle fails it without looking at the content.

## Fidelity changes

- **Allowed domains: none** (stricter). Upstream sets `allow_internet = true`;
  the reference needs no network (it uses the `rustc` already in the image), so
  the pack allows no domain. An agent that would download a tool or a crate
  cannot.
- **The decompressor runs once, directly on the file, not through `cat`**
  (equivalent). The test pipes `cat /app/data.comp` into `decomp2`; the adapter
  gives the file as standard input. `getchar` reads the same bytes either way.
  When `/app/data.comp` is missing or not a regular file, `cat` fails and the
  decompressor reads an empty stream; the adapter then gives it `/dev/null`.
  Such a candidate already fails `data-comp`.
- **Upstream's `setup()` writes into `/app`; the pack does not** (more
  lenient). Before each test, upstream copies `original-decomp.c` and
  `original-data.txt` over `/app/decomp.c` and `/app/data.txt` and runs
  `gcc -o decomp2 decomp.c` in `/app` with `check=True`. The adapter instead
  compiles the pack's copy of `decomp.c` in a fresh temporary directory, with
  the same compiler and command, and the Oracle reads `data.txt` from
  `hidden/`. As a result, leftovers in `/app` that break upstream's setup make
  native fail a candidate whose `data.comp` is correct, while SecureBench passes
  it. Examples: a directory at `/app/decomp2` (`ld: cannot open output file
  decomp2: Is a directory`), a directory at `/app/decomp.c` or
  `/app/data.txt`, or `/app/data.txt` as a symlink to `data.comp`
  (`shutil.copy` writes through it and overwrites `data.comp`). The conversion
  deliberately trusts no file under `/app` other than `data.comp`, so that a
  candidate cannot swap the decompressor or the expected text
  (`attack-swap-decompressor`, `attack-rewrite-data`). No plausible solution
  leaves these obstacles behind.
- **`/app/data.comp` must be a regular file** (stricter). Upstream's
  `Path.exists()` and `stat()` follow symlinks, so a symlink inside `/app`
  pointing to a valid compressed file passes upstream. The artifact check reports
  a symlink as `not_regular` and the Oracle fails it. The instructions ask for a
  file `data.comp`, and no plausible solution writes a symlink there.
- **A symlink that points outside `/app` fails the capture** (stricter).
  Symlinks that stay inside `/app` are captured (`symlinks = true`). A symlink
  anywhere under `/app` that points outside it, including `/app/data.comp`
  itself, fails the capture (class `capture`), where upstream passes if
  `data.comp` resolves to a valid file. This mostly affects build trees an
  agent leaves behind; the reference leaves no symlink.
- **The output passed to the Oracle is bounded at 64 KiB** (equivalent; see
  above).

## Candidates

- `reference.sh` changes to `/app` and runs `upstream-solve.bash`, which is
  upstream's `solution/solve.sh` byte for byte.
- `mutant-literals-only.sh` builds `literals-only.c`, a correct encoder for the
  format that emits only literals. Its 4,576-byte output decompresses to
  `data.txt` exactly (checked by hand with the `-O0` decompressor), so it fails
  on the size bound alone.
- `mutant-padded.sh` pads the reference output with zero bytes to exactly 2500
  bytes, the inclusive limit.
- `mutant-crlf.sh`, `mutant-cr.sh` and `mutant-cp1252.sh` run the reference
  compressor on `data.txt` with CRLF line endings, lone CR line endings, and
  en dashes re-encoded as the Windows-1252 byte `0x96`.
- `attack-swap-decompressor.sh` replaces `/app/decomp.c`, `/app/decomp` and
  `/app/decomp2` with a program that prints `data.txt`; `attack-rewrite-data.sh`
  overwrites `/app/data.txt` with the output of a 4-byte `data.comp`;
  `attack-hijack-runner.sh` plants stdlib-shadowing Python modules,
  `sitecustomize.py`, `usercustomize.py` and an outcome-rewriting `conftest.py`
  in `/app`. Each writes a 4-byte `data.comp`.

| Candidate | SecureBench | Native |
|---|---|---|
| reference | passed | 1.0 |
| null | failed (oracle) | 0.0 |
| mutant-literals-only | failed (oracle) | 0.0 |
| mutant-padded | passed | 1.0 |
| mutant-crlf | passed | 1.0 |
| mutant-cr | passed | 1.0 |
| mutant-cp1252 | failed (oracle) | 0.0 |
| attack-swap-decompressor | failed (oracle) | 0.0 |
| attack-rewrite-data | failed (oracle) | 0.0 |
| attack-hijack-runner | failed (oracle) | 0.0 |

## Divergences from native

None. Every candidate gets the same verdict from both graders.

## Review

Reviewer: acdefcc2c957d9c99, 2026-10-27 (second review, after the converter addressed the first review's findings)

Pack digest reviewed: `sha256:efb88403d6829e28e0e67c9a83486dd10718ee41fdaf169921d175ebb8caf67d` (`securebench validate`). It is unchanged since the first review: the fixes touched only `CONVERSION.md`. Every SecureBench run in `qualification.json` records this digest, `problems` is empty, and every run was rejudged.

1. Instructions. `cmp task/instructions.md` against upstream `instruction.md`: identical.
2. Scope. One root, `/app`, the only place the deliverable `/app/data.comp` can be, with room for any compressor build tree. The baseline's `/app` holds only `data.txt`, `decomp` and `decomp.c` and has no symlinks (checked in the image). Nothing in the Evaluation runs or imports candidate files: the adapter runs the stock Python with `-I` (the cwd `/app` is not on `sys.path`), compiles `evaluation/decomp.c` with `/usr/bin/gcc` in a temporary directory, and only feeds `/app/data.comp` to the binary as data. So there are no test files or convention-loaded files to exclude. The symlink rules are now labelled stricter (see findings below).
3. Expected values. The only expected value is `hidden/data.txt`, identical to upstream's `tests/original-data.txt` and to the image's `/app/data.txt` (same SHA-256). It is necessarily public: it is the input the agent must compress. The Oracle reads it from `hidden/`, never from the Evaluation, so a candidate that rewrites `/app/data.txt` gains nothing (`attack-rewrite-data`). `evaluation/` holds only the decompressor source (identical to `tests/original-decomp.c`), the adapter and the schemas. No allowed domains.
4. Challenges. The single challenge is `{}`.
5. Cases. One case, for upstream's one decompression test. The seed is not used, because upstream's tests draw nothing at random.
6. Oracle. `oracle.py` holds no expected value; 2500 is upstream's threshold and 65,536 is an output bound. It checks every observation field and requires the adapter to return normally. It bounds its work: the schema caps the base64 at 87,384 bytes, and output above 65,536 bytes fails without decoding, since it cannot equal the 4,860-character text. It reproduces the decoding of `subprocess.run(text=True)` exactly: strict UTF-8, which native Python 3.13 uses under the image's unset locale, and the same two `replace` calls as `_translate_newlines`. The artifact check reads the size from the captured file. The decompressor prints a buffer with no terminating zero byte, but its output is stable: 402 runs of the reference `data.comp` with varying environment sizes and binary paths all matched `data.txt`.
7. Candidates. `upstream-solve.bash` is byte-identical to upstream `solution/solve.sh`; `reference.sh` adds only `cd /app`. I re-ran the mutant encodings in the image. `crlf` is 2265 bytes, `cr` 2264, `cp1252` 2257 and `padded` exactly 2500, and all exit 0. So each mutant reaches the place it aims at (newline translation, strict decoding, the size boundary) instead of failing early. `literals-only` aims at the size bound. The attacks target this task's real routes: swapping the decompressor, rewriting `data.txt` and shadowing the adapter's modules. Candidates are unchanged since the first review.
8. Divergences. None. Every candidate gets the same verdict from both graders, and "Divergences from native" now says so.
9. Inventory. No row yet (the coordinator adds it on approval). The row should be `converted`; no Section 11 reason applies (no speed target, no network or privileges needed at grading).

Upstream assertions: `compressed_path.exists()` (tests 1 to 3) and `file_size <= 2500` map to `data-comp`. `decompressor_path.exists()` maps to the adapter's `unable` on a failed compile. `original_path.exists()` holds trivially, because the file is in `hidden/`. `returncode == 0` and `stdout == original_content` map to `decompress`. None is dropped.

Findings of the first review, re-checked:
- Fixed. Upstream's `setup()` writes into `/app` and the pack does not. This is now its own fidelity change, labelled more lenient, with the obstacles that make native fail a correct `data.comp` and the reason: the pack trusts no file under `/app` other than `data.comp`. The obstacles are a directory at `/app/decomp2`, `/app/decomp.c` or `/app/data.txt`, and `/app/data.txt` as a symlink to `data.comp`.
- Fixed. The symlink bullet is now labelled stricter, and it covers `/app/data.comp` pointing outside `/app`.
- Fixed. "Divergences from native" says there are none, which matches `qualification.json`.

Findings:
- None.

Verdict: approved
