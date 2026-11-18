"""Differential test of the adapter and Oracle against upstream's test (CONVERSION.md, "Oracle arithmetic").

Two steps. First, where numpy is installed (the baseline has 2.2.5; upstream's
verifier uses 2.3.1), save arrays near upstream's threshold as .npy files, and
record for each one upstream's own verdict (the matching loop of
tests/test_outputs.py, copied below, with any exception a failure) and the
observation the adapter's own `load()` reports for that file:

    docker run --rm --network none --memory 2g -v "$PWD/task:/t:ro" <image> \
        python3 -I /t/hidden/differential.py generate /t/evaluation/adapter.py 1 3000 > corpus.jsonl

Then, on the host, judge each observation with the Oracle against upstream's A1
and count the verdicts that differ:

    uv run python -B task/hidden/differential.py compare task corpus.jsonl

The arrays cover every way upstream's loop reads one: (n, 10) rows of float64,
float32, float16, integers, booleans and complex numbers, one of them close to
the tolerance; 1-D arrays and (n, 1) arrays of small numbers, whose single value
per entry broadcasts across a row; (n, p, 10) and (n, p, 1) entries, up to
40,960 values in one entry so that numpy's buffered summation is exercised;
entries holding inf or NaN; shapes and types that upstream rejects or that
have no elements; arrays of three or more dimensions saved in Fortran order,
including ones whose verdict upstream depends on that order; and one known
difference, a long double array beyond double's range.
"""

import importlib.util
import json
import os
import random
import sys
import tempfile


def upstream(a, b) -> bool:
    import numpy as np

    try:
        for original_row in a:
            row_matched = False
            for stolen_row in b:
                ratio_diff = np.abs(stolen_row / original_row - np.mean(stolen_row / original_row))
                if np.all(ratio_diff < 1e-4):
                    row_matched = True
                    break
            if not row_matched:
                return False
        return True
    except Exception:
        return False


def generate(adapter_path: str, seed: int, count: int) -> None:
    import warnings

    import numpy as np

    warnings.simplefilter("ignore")
    source = open(adapter_path).read().split("challenge = json.loads")[0]
    adapter: dict[str, object] = {}
    exec(compile(source, adapter_path, "exec"), adapter)
    np.random.seed(5)
    a1 = np.random.randn(30, 10) * 0.3
    rng = random.Random(seed)

    def deviation(entry, row) -> float:
        """Upstream's largest deviation for one entry against one row of A1."""
        ratios = entry / row
        return float(np.max(np.abs(ratios - np.mean(ratios))))

    def near(value: float) -> float:
        """value, off by a relative 1e-16 to 1e-3 to either side."""
        return value * (1 + rng.choice([-1, 1]) * 10 ** rng.uniform(-16, -3))

    def rows(kind: str):
        # The other rows are exact multiples of A1's rows at scales of 1 or more:
        # at small scales upstream's absolute tolerance matches a row to every
        # row of A1, and the designated row would no longer decide.
        b = np.array([rng.choice([1, -1]) * 10 ** rng.uniform(0, 3) * row for row in a1])
        i = rng.randrange(30)
        d = np.array([rng.uniform(-1, 1) for _ in range(10)])
        if kind.startswith("complex"):
            k = complex(rng.gauss(0, 1), rng.gauss(0, 1)) * 10 ** rng.uniform(-4, 2)
            d = d + 1j * np.array([rng.uniform(-1, 1) for _ in range(10)])
            b = b.astype(complex)
        else:
            k = rng.choice([1.0, -1.0]) * 10 ** rng.uniform(-6, 3)
        # Scale the noise so that the row's largest deviation lies next to 1e-4.
        d = d * near(1e-4) / deviation((k + d) * a1[i], a1[i])
        b[i] = (k + d) * a1[i]
        if rng.random() < 0.2:
            b = np.concatenate([b, rng.uniform(-1, 1) * np.ones((rng.randrange(1, 4), 10)) * b[0]])
        if rng.random() < 0.15:
            bad = b[:1].copy()
            bad[0, rng.randrange(10)] = rng.choice([np.nan, np.inf, -np.inf])
            b = np.concatenate([bad, b])
        b = b[np.array(rng.sample(range(len(b)), len(b)))]
        return b.astype({"float64": np.float64, "float32": np.float32, "float16": np.float16, "complex": np.complex128, "complex64": np.complex64}[kind])

    def small(shape_tail: tuple[int, ...], entries: int, complex_values: bool):
        """Entries of small values, each scaled so that its deviation against the hardest row of A1 lies next to 1e-4."""
        b = []
        for _ in range(entries):
            entry = np.array([rng.uniform(-1, 1) for _ in range(int(np.prod(shape_tail)))]).reshape(shape_tail)
            if complex_values:
                entry = entry * complex(rng.uniform(-1, 1), rng.uniform(-1, 1))
            hardest = max(deviation(entry, row) for row in a1)
            b.append(entry * near(1e-4) / hardest)
        b = np.array(b)
        if rng.random() < 0.2:
            b.reshape(-1)[rng.randrange(b.size)] = rng.choice([np.nan, np.inf])
        return b

    def stacked():
        p = rng.choice([rng.randrange(2, 5), rng.randrange(20, 61)])
        b = np.array([[rng.choice([1, -1]) * 10 ** rng.uniform(-3, 2) * row] * p for row in a1])
        i = rng.randrange(30)
        k = 10 ** rng.uniform(-3, 1)
        e = np.array([[rng.uniform(-1, 1) for _ in range(10)] for _ in range(p)])
        e = e * near(1e-4) / deviation((k + e) * a1[i], a1[i])
        b[i] = (k + e) * a1[i]
        return b

    def flips():
        """Fortran-ordered (30, 50, 10) arrays whose verdict upstream differs from that of their C-ordered copy."""
        found = []
        for attempt in range(20):
            b = np.array([[row] * 50 for row in a1])
            b[0] = a1[0] * 3.0 * (1 + np.array([[rng.gauss(0, 1) for _ in range(10)] for _ in range(50)]) * 1e-9)
            f = np.asfortranarray(b)
            mean = np.mean(f[0] / a1[0])
            start = a1[0, 0] * (mean + 1e-4 / (1 - 1 / 500))
            for direction in (np.inf, -np.inf):
                x = start
                for _ in range(3000):
                    f[0, 0, 0] = x
                    entry = f[0]
                    if (deviation(entry, a1[0]) < 1e-4) != (deviation(np.ascontiguousarray(entry), a1[0]) < 1e-4):
                        found.append(f.copy(order="F"))
                        break
                    x = np.nextafter(x, direction)
            if len(found) >= 4:
                break
        return found

    fixed = [
        np.array(0.0), np.zeros(0), np.zeros(5), np.zeros((2, 1)), np.zeros((1, 0, 10)), np.zeros((3, 0, 1)),
        np.zeros((2, 0)), np.zeros((0, 10)), np.zeros((1, 0)), np.zeros((4, 3, 0, 10)), np.zeros((1, 50000, 0, 10)), a1.copy(), a1.T.copy(),
        a1[None].copy(), a1[..., None].copy(), np.zeros((1, 10), int), np.zeros((1, 10), bool), np.ones((1, 10), bool),
        np.array([["a"] * 10]), np.zeros((1, 10), "m8[s]"), a1.astype(np.float16), a1 * (1 + 2j), a1.astype(np.longdouble),
        (a1 * 3).astype(np.int64), np.full((30, 10), np.nan), np.concatenate([a1, np.full((1, 10), np.inf)]),
        np.array([1e308] * 10)[None] * np.sign(a1[:1]), a1 * 1e300, a1 * 1e-300,
    ]
    makers = [
        ("rows-float64", lambda: rows("float64")),
        ("rows-complex128", lambda: rows("complex")),
        ("rows-float32", lambda: rows("float32")),
        ("rows-float16", lambda: rows("float16")),
        ("rows-complex64", lambda: rows("complex64")),
        ("scalars", lambda: small((), rng.randrange(1, 3), False)),
        ("scalars-complex", lambda: small((), rng.randrange(1, 3), True)),
        ("column", lambda: small((1,), rng.randrange(1, 3), False)),
        ("columns-3d", lambda: small((rng.randrange(1, 4), 1), rng.randrange(1, 3), rng.random() < 0.3)),
        ("stacked-3d", stacked),
    ]
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "stolen_A1.npy")
        adapter["STOLEN"] = path
        samples = [("fixed", b) for b in fixed]
        samples += [("fortran-flip", b) for b in flips()]
        # Known difference (CONVERSION.md, "Element types"): long double values
        # beyond double's range become infinite here.
        samples.append(("longdouble-beyond-double", a1.astype(np.longdouble) * np.longdouble(2) ** 1400))
        samples += [("big", small((rng.randrange(800, 4097), 1), 1, rng.random() < 0.5)) for _ in range(max(4, count // 100))]
        for _ in range(count):
            layout, maker = rng.choice(makers)
            b = maker()
            # np.mean sums an entry of a Fortran-ordered array of three or more
            # dimensions in Fortran order.
            if b.ndim >= 3 and rng.random() < 0.5:
                layout, b = layout + "-fortran", np.asfortranarray(b)
            samples.append((layout, b))
        for layout, b in samples:
            np.save(path, b)
            record = {
                "layout": layout,
                "shape": list(b.shape),
                "dtype": b.dtype.str,
                "upstream": upstream(a1, np.load(path)),
                "observation": adapter["load"](),
            }
            print(json.dumps(record, allow_nan=False))
    print(json.dumps({"numpy": np.__version__}))


def compare(task: str, corpus_path: str) -> None:
    sys.path.insert(0, os.getcwd())
    from securebench.core.evidence import CaseEvidence, Ending, HostFacts, Observed

    spec = importlib.util.spec_from_file_location("oracle", os.path.join(task, "hidden", "oracle.py"))
    assert spec is not None and spec.loader is not None
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    with open(os.path.join(task, "hidden", "cases.json")) as file:
        context = {"name": "upstream", "a1": json.load(file)[0]["a1"]}
    totals: dict[str, list[int]] = {}
    differences = []
    version = "?"
    with open(corpus_path) as file:
        for line in file:
            record = json.loads(line)
            if "numpy" in record:
                version = record["numpy"]
                continue
            observation = {"ending": "exited", "exit_status": 0, "stderr_tail": "", **record["observation"]}
            evidence = CaseEvidence("steal", 0, "", HostFacts(Ending.RETURNED, 0, 0.0), Observed(observation), ())
            verdict = oracle.judge("steal", context, evidence).passed
            total = totals.setdefault(record["layout"], [0, 0, 0])
            total[0] += 1
            total[1] += record["upstream"]
            if verdict != record["upstream"]:
                total[2] += 1
                differences.append((record["shape"], record["dtype"], record["upstream"], verdict))
    print(f"numpy {version}")
    for layout, (n, accepted, differ) in totals.items():
        print(f"  {layout}: {n} arrays, {accepted} accepted by upstream, {differ} verdicts differ")
    for difference in differences[:20]:
        print("  differs:", difference)


if sys.argv[1] == "generate":
    generate(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
else:
    compare(sys.argv[2], sys.argv[3])
