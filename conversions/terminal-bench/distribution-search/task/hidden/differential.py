"""Differential test of the Oracle against upstream's tests on numpy 2.3.0 (lesson C57).

Not used by the Oracle. It runs inside the baseline image, with numpy 2.3.0 and
pytest 8.4.1 (the versions upstream's verifier installs) in /np230, the
SecureBench repository at /repo, upstream's tests at /tests and this pack at
/pack, all read-only:

    pip install --target <dir> numpy==2.3.0 pytest==8.4.1   # once, with network
    docker run --rm --network none --memory 2g --cpus 1 \
      -v <dir>:/np230:ro -v <repository>:/repo:ro \
      -v <upstream>/distribution-search/tests:/tests:ro -v <pack>:/pack:ro \
      -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/np230:/repo \
      <baseline image> python3 /pack/hidden/differential.py

It checks three things:

1. `pairwise_sum` equals np.sum bit for bit (`buffered_sum` for big-endian
   arrays), and math.log equals np.log, on random float64 arrays.
2. On every file of a corpus weighted toward the acceptance thresholds, the
   verdict of upstream's four test functions (numpy 2.3.0) equals the verdict
   of the adapter (baseline numpy) and the judge. Each threshold is located by
   bisection on upstream's own computation, so the corpus holds the last file
   that upstream accepts and the first that it rejects.
3. For float32 files, how far the judge's float64 values lie from upstream's
   float32 arithmetic.
"""

import importlib.util
import json
import math
import subprocess
import sys

import numpy as np

sys.path.insert(0, "/pack/hidden")

import oracle

from securebench.core import jsondata
from securebench.core.evidence import (
    CaseEvidence,
    Ending,
    HostFacts,
    Observed,
    Unable,
)


class Resources:
    """The pack's hidden/ files, read as SecureBench's own resources read them."""

    def read(self, relative_path: str) -> bytes:
        with open(f"/pack/hidden/{relative_path}", "rb") as handle:
            return handle.read()

    def read_json(self, relative_path: str) -> object:
        data = self.read(relative_path)
        return jsondata.decode(data, len(data))


# The one case's context, from hidden/cases.json through the Oracle's own plan.
CONTEXT = oracle.plan(Resources(), 0).cases["distribution"][0].context

V = 150_000
LOG_V = math.log(V)
PATH = "/app/dist.npy"
ADAPTER = ["/usr/local/bin/python3", "-I", "/pack/evaluation/adapter.py"]

spec = importlib.util.spec_from_file_location("upstream", "/tests/test_outputs.py")
assert spec is not None and spec.loader is not None
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)
TESTS = (
    "test_distribution_file_exists",
    "test_distribution_shape",
    "test_distribution_validity",
    "test_kl_divergences",
)


def native(array: np.ndarray) -> bool:
    np.save(PATH, array)
    for name in TESTS:
        try:
            getattr(upstream, name)()
        except BaseException:
            return False
    return True


def securebench(array: np.ndarray) -> tuple[bool, object]:
    np.save(PATH, array)
    ran = subprocess.run(ADAPTER, input=b"{}", capture_output=True, cwd="/app", check=True)
    response = json.loads(ran.stdout)
    outcome = (
        Observed(response["observation"])
        if "observation" in response
        else Unable(**response["unable"])
    )
    facts = HostFacts(Ending.RETURNED, 0, 0.0)
    evidence = CaseEvidence("distribution", 0, "", facts, outcome, ())
    judgment = oracle.judge("distribution", CONTEXT, evidence)
    return judgment.passed, judgment.diagnostic


def three_levels(heavy: int, middle: int, forward: float, backward: float) -> np.ndarray:
    """Solve a three-level distribution with Newton's method on its log levels, as upstream does."""
    light = V - heavy - middle
    counts = np.array([heavy, middle, light], dtype=float)
    x = np.array([-5.0, -12.0, -22.0])
    for _ in range(200):
        p = np.exp(x)
        residual = np.array(
            [
                counts @ p - 1.0,
                counts @ x + V * (LOG_V + backward),
                counts @ (p * x) - (forward - LOG_V),
            ]
        )
        jacobian = np.array([counts * p, counts, counts * p * (x + 1.0)])
        step = np.linalg.solve(jacobian, -residual)
        scale = 1.0
        while scale > 1e-6 and np.max(np.abs(step * scale)) > 2.0:
            scale /= 2
        x = np.minimum(x + scale * step, 0.0)
        if np.max(np.abs(residual)) < 1e-13:
            break
    levels = np.exp(x)
    array = np.repeat(levels, [heavy, middle, light])
    return array / array.sum()


def kl_ok(array: np.ndarray) -> tuple[bool, bool]:
    p = array / array.sum()
    forward, backward = upstream.kl_forward(p), upstream.kl_backward(p)
    return abs(forward - 10.0) <= 1e-3, abs(backward - 10.0) <= 1e-3


def boundary(make, accepted) -> list[np.ndarray]:
    """Bisect t so that `accepted(make(t))` flips; return the files on both sides."""
    low, high = -1e-6, 1e-6
    assert accepted(make(low)) != accepted(make(high))
    side = accepted(make(low))
    for _ in range(80):
        middle = (low + high) / 2
        if middle in (low, high):
            break
        if accepted(make(middle)) == side:
            low = middle
        else:
            high = middle
    return [make(low), make(high)]


def corpus() -> list[tuple[str, np.ndarray]]:
    reference = three_levels(7500, 1, 10.0, 10.0)
    files = [("reference-like", reference)]
    for heavy, middle in ((7000, 5), (7600, 300), (5000, 2000), (9000, 13)):
        files.append((f"three-levels-{heavy}-{middle}", three_levels(heavy, middle, 10.0, 10.0)))
    for edge in (10.001, 9.999):
        files += [
            (f"forward-edge-{edge}-{i}", f)
            for i, f in enumerate(
                boundary(
                    lambda t, e=edge: three_levels(7500, 1, e + t, 10.0), lambda a: kl_ok(a)[0]
                )
            )
        ]
        files += [
            (f"backward-edge-{edge}-{i}", f)
            for i, f in enumerate(
                boundary(
                    lambda t, e=edge: three_levels(7500, 1, 10.0, e + t), lambda a: kl_ok(a)[1]
                )
            )
        ]
        files += [
            (f"both-edge-{edge}-{i}", f)
            for i, f in enumerate(
                boundary(
                    lambda t, e=edge: three_levels(7500, 1, e + t, e + t), lambda a: all(kl_ok(a))
                )
            )
        ]
    for sign in (1.0, -1.0):
        files += [
            (f"sum-edge-{sign:+}-{i}", f)
            for i, f in enumerate(
                boundary(
                    lambda t, s=sign: reference * (1.0 + s * 1e-5 + t),
                    lambda a: bool(abs(a.sum() - 1.0) < 1e-5),
                )
            )
        ]
    spike = np.full(V, 5e-324)
    spike[0] = 1.0
    files += [("max-one", spike), ("big-endian", reference.astype(">f8"))]
    zero = reference.copy()
    zero[-1] = 0.0
    files.append(("one-zero", zero))
    return files


def main() -> None:
    rng = np.random.default_rng(20261012)
    for size in [*range(1, 300), 1023, 8191, 8192, 8193, 65536, 149999, V]:
        for scale in (1.0, 1e-6, 1e6):
            array = rng.standard_normal(size) * scale
            assert float(np.sum(array)) == oracle.pairwise_sum(array.tolist()), size
            assert float(np.sum(array.astype(">f8"))) == oracle.buffered_sum(array.tolist()), size
    positive = np.concatenate([rng.random(V), rng.random(V) ** 20, np.exp(-rng.random(V) * 700)])
    positive = positive[positive > 0]
    logs = np.log(positive)
    mismatched = sum(float(n) != math.log(float(x)) for n, x in zip(logs, positive, strict=True))
    print(
        f"pairwise_sum and buffered_sum == np.sum (native and big-endian) on {299 + 7} sizes"
        f" x 3 scales; np.log != math.log on {mismatched} of {positive.size}"
    )

    disagreements = 0
    unequal = 0
    for name, array in corpus():
        expected = native(array)
        passed, diagnostic = securebench(array)
        disagreements += expected != passed
        measured = diagnostic.get("measured") if isinstance(diagnostic, dict) else None
        if measured:
            p = array / array.sum()
            native_values = (float(array.sum()), upstream.kl_forward(p), upstream.kl_backward(p))
            if native_values != (measured["sum"], measured["forward"], measured["backward"]):
                unequal += 1
                print(f"not bit-equal: {name} native {native_values}")
        print(f"{name:28} native={int(expected)} securebench={int(passed)} {json.dumps(measured)}")
    print(
        f"float64 corpus disagreements: {disagreements};"
        f" files with sum or KL not bit-equal: {unequal}"
    )

    gaps: list[float] = []
    disagreements = 0
    for name, array in corpus():
        single = array.astype(np.float32)
        expected = native(single)
        passed, diagnostic = securebench(single)
        disagreements += expected != passed
        p = single / single.sum()
        native_values = (upstream.kl_forward(p), upstream.kl_backward(p))
        measured = diagnostic.get("measured") if isinstance(diagnostic, dict) else None
        if measured:
            gaps += [
                abs(native_values[0] - measured["forward"]),
                abs(native_values[1] - measured["backward"]),
            ]
        if expected != passed:
            print(
                f"float32 {name:28} native={int(expected)} securebench={int(passed)}"
                f" {native_values} {json.dumps(measured)}"
            )
    print(f"float32 corpus disagreements: {disagreements}; largest KL gap {max(gaps):.3g}")

    for name, data in files(three_levels(7500, 1, 10.0, 10.0)):
        verdicts = int(native_bytes(data)), int(securebench_bytes(data))
        print(f"file {name:24} native={verdicts[0]} securebench={verdicts[1]}")


def native_bytes(data: bytes) -> bool:
    with open(PATH, "wb") as out:
        out.write(data)
    for name in TESTS:
        try:
            getattr(upstream, name)()
        except BaseException:
            return False
    return True


def securebench_bytes(data: bytes) -> bool:
    with open(PATH, "wb") as out:
        out.write(data)
    ran = subprocess.run(ADAPTER, input=b"{}", capture_output=True, cwd="/app", check=True)
    response = json.loads(ran.stdout)
    outcome = (
        Observed(response["observation"])
        if "observation" in response
        else Unable(**response["unable"])
    )
    evidence = CaseEvidence("distribution", 0, "", HostFacts(Ending.RETURNED, 0, 0.0), outcome, ())
    return oracle.judge("distribution", CONTEXT, evidence).passed


def files(reference: np.ndarray) -> list[tuple[str, bytes]]:
    """Ways of writing the reference that do not go through a plain np.save of float64."""
    import io
    import zipfile

    def saved(array: np.ndarray, **options: object) -> bytes:
        buffer = io.BytesIO()
        np.save(buffer, array, **options)
        return buffer.getvalue()

    def versioned(version: tuple[int, int]) -> bytes:
        buffer = io.BytesIO()
        np.lib.format.write_array(buffer, reference, version=version)
        return buffer.getvalue()

    plain = saved(reference)
    fortran = plain.replace(b"'fortran_order': False", b"'fortran_order': True ")
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("dist.npy", plain)
    with np.errstate(all="ignore"):
        return [
            ("version-2.0", versioned((2, 0))),
            ("version-3.0", versioned((3, 0))),
            ("fortran-order-1d", fortran),
            ("trailing-bytes", plain + b"\x00" * 64),
            ("truncated", plain[:-8]),
            ("column", saved(reference.reshape(-1, 1))),
            ("npz", archive.getvalue()),
            ("object-array", saved(reference.astype(object), allow_pickle=True)),
            ("raw-tofile", reference.tobytes()),
            ("float16", saved(reference.astype(np.float16))),
            ("longdouble", saved(reference.astype(np.longdouble))),
            ("complex128", saved(reference.astype(np.complex128))),
            ("int64", saved((reference * 1e9).astype(np.int64))),
        ]


main()
