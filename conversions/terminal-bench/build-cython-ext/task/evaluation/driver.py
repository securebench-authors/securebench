"""build-cython-ext driver: call the candidate's pyknotid and report what it returned.

It runs on the baseline's own interpreter, /usr/local/bin/python3, because the
candidate's compiled extensions are built for it. The adapter starts it with
`-I`, the challenge on standard input and the mode as its only argument:

- `outputs`, from /app: the calls of upstream tests/test_outputs.py, with the
  inputs the challenge gives (upstream's own).
- `repository`, from /app/pyknotid, with that directory first on sys.path as
  upstream's `python -m pytest` has it: the calls of pyknotid 0.5.3's own
  tests/test_knot.py and tests/test_spacecurve.py.

Assertion-free: every expected value stays with the Oracle. Each upstream test
becomes one record holding the values its assertions compare, or the exception
it raised. Where an assertion compares two values the candidate produces (a copy
against its original), the record holds the outcome of that comparison.

Candidate code prints progress to standard output, so the driver moves its own
standard output aside first and writes only its JSON result there.
"""

import importlib.util
import json
import math
import numbers
import os
import sys

RESULT = os.fdopen(os.dup(1), "w", encoding="utf-8")
os.dup2(2, 1)

MAX_ERROR_BYTES = 1000
MAX_TEXT_CHARACTERS = 4096
LARGEST = 1e300


class Unreportable(Exception):
    """A value the observation schema cannot carry."""


def error_text(error: BaseException) -> str:
    try:
        text = f"{type(error).__name__}: {error}"
    except Exception:
        text = type(error).__name__
    return text.encode("utf-8", "replace")[:MAX_ERROR_BYTES].decode("utf-8", "ignore")


def real(value: object) -> float:
    # Only real numbers: a string or an array never becomes a number here.
    if not isinstance(value, numbers.Real):
        raise Unreportable(f"not a real number: {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number) or abs(number) > LARGEST:
        raise Unreportable(f"not a finite number: {number!r}")
    return number


def text(value: object) -> str:
    if not isinstance(value, str):
        raise Unreportable(f"not a string: {type(value).__name__}")
    if len(value) > MAX_TEXT_CHARACTERS:
        raise Unreportable(f"string longer than {MAX_TEXT_CHARACTERS} characters")
    return value


# ---- outputs: upstream tests/test_outputs.py ----


def numpy_version() -> dict[str, object]:
    try:
        import numpy

        return {"error": "", "text": text(numpy.__version__)}
    except BaseException as error:
        return {"error": error_text(error), "text": ""}


def spec(module: str) -> dict[str, object]:
    record: dict[str, object] = {"module": module, "error": "", "found": False, "loader": []}
    try:
        found = importlib.util.find_spec(module)
        if found is not None:
            record["found"] = True
            record["loader"] = [
                text(f"{cls.__module__}.{cls.__qualname__}")[:256]
                for cls in type(found.loader).__mro__[:64]
            ]
    except BaseException as error:
        record["error"] = error_text(error)
    return record


def cross(inputs: list[float]) -> dict[str, object]:
    try:
        import pyknotid.spacecurves.chelpers as ch

        return {"error": "", "value": real(ch.cross_product(*inputs))}
    except BaseException as error:
        return {"error": error_text(error), "value": 0.0}


def writhe(item: dict[str, list]) -> dict[str, object]:
    try:
        import numpy as np
        import pyknotid.spacecurves.ccomplexity as cc

        points = np.array(item["points"], dtype=np.float64)
        contributions = np.array(item["contributions"], dtype=np.float64)
        order = np.array(item["order"], dtype=np.int64)
        return {"error": "", "value": real(cc.cython_higher_order_writhe(points, contributions, order))}
    except BaseException as error:
        return {"error": error_text(error), "value": 0.0}


def knot(item: dict[str, object]) -> dict[str, object]:
    try:
        import pyknotid.invariants as inv
        import pyknotid.make as mk
        import pyknotid.spacecurves as sp

        maker = {"trefoil": mk.trefoil, "figure_eight": mk.figure_eight, "three_twist": mk.three_twist}
        k = sp.Knot(maker[item["knot"]](num_points=item["num_points"]))
        if item["op"] == "vassiliev_degree_3":
            gc = k.gauss_code()
            cy_result = inv.vassiliev_degree_3(gc, try_cython=True)
            py_result = inv.vassiliev_degree_3(gc, try_cython=False)
            values = [real(cy_result), real(py_result)]
        elif item["op"] == "alexander_polynomial":
            values = [real(k.alexander_polynomial(-1))]
        else:
            values = [real(k.determinant())]
        return {"error": "", "values": values}
    except BaseException as error:
        return {"error": error_text(error), "values": []}


def outputs(challenge: dict[str, list]) -> dict[str, object]:
    return {
        "numpy_version": numpy_version(),
        "specs": [spec(module) for module in challenge["specs"]],
        "cross": [cross(inputs) for inputs in challenge["cross"]],
        "writhe": [writhe(item) for item in challenge["writhe"]],
        "knots": [knot(item) for item in challenge["knots"]],
    }


# ---- repository: pyknotid 0.5.3 tests/test_knot.py and tests/test_spacecurve.py ----
# Each function reproduces one test body and returns (numbers, series, flags,
# texts): the values its assertions compare, in the order they appear.


def knot_trefoil():
    import pyknotid.make as mk
    import pyknotid.spacecurves.knot as spknot

    return spknot.Knot(mk.trefoil())


def curve_trefoil():
    import pyknotid.make as mk
    import pyknotid.spacecurves.spacecurve as sp

    return sp.SpaceCurve(mk.trefoil())


def test_invariants():
    k = knot_trefoil()
    determinant = real(k.determinant())
    roots = k.alexander_at_root((2, 3, 4))
    kind = type(roots).__name__
    series = [real(value) for value in roots] if isinstance(roots, (list, tuple)) else []
    return [determinant, real(k.vassiliev_degree_2()), real(k.vassiliev_degree_3())], series, [], [text(kind)]


def test_identify():
    knot_trefoil()
    try:
        import pyknotid.spacecurves.chelpers  # noqa: F401
    except ImportError:
        pass
    return [], [], [], []


def test_init():
    curve_trefoil()
    return [], [], [], []


def test_copy():
    import numpy as np

    k = curve_trefoil()
    k2 = k.copy()
    return [], [], [bool(np.all(k2.points == k.points)), k2.points is not k.points], []


def test_points():
    import numpy as np

    k = curve_trefoil()
    return [], [], [isinstance(k.points, np.ndarray)], []


def test_translate():
    k = curve_trefoil()
    pos = k.points[0]
    k.translate([10.0, 20.0, 30.0])
    new_pos = k.points[0]
    return [], [real(new_pos[i] - pos[i]) for i in range(3)], [], []


def test_zero_centroid():
    import numpy as np

    k = curve_trefoil()
    k.points += np.random.random(size=3) * np.random.random() * 10
    k.zero_centroid()
    return [], [real(value) for value in np.ravel(np.average(k.points, axis=0))], [], []


def test_rotate():
    curve_trefoil().rotate()
    return [], [], [], []


def test_planar_writhe():
    import numpy as np

    return [real(np.abs(curve_trefoil().planar_writhe()))], [], [], []


def test_writhe():
    k = curve_trefoil()
    k.rotate()
    return [real(k.writhe(100))], [], [], []


def test_gauss_code():
    return [], [], [], [text(str(curve_trefoil().gauss_code(recalculate=True)))]


def test_reconstructed_space_curve():
    k = curve_trefoil()
    k2 = k.reconstructed_space_curve()
    return [real(k.planar_writhe()), real(k2.planar_writhe())], [], [], []


def test_write_load():
    import pyknotid.spacecurves.spacecurve as sp

    k = curve_trefoil()
    k.to_json("test_trefoil.json")
    k2 = sp.SpaceCurve.from_json("test_trefoil.json")
    first = real(k2.planar_writhe())
    second = real(k2.planar_writhe())
    os.unlink("test_trefoil.json")
    return [first, second], [], [], []


def test_octree_simplify():
    curve_trefoil().octree_simplify(runs=2)
    return [], [], [], []


def test_arclength():
    return [real(curve_trefoil().arclength())], [], [], []


def test_rog():
    return [real(curve_trefoil().radius_of_gyration())], [], [], []


def test_smooth():
    curve_trefoil().smooth()
    return [], [], [], []


def test_compiled_vs_python_find_crossings():
    k = curve_trefoil()
    try:
        import pyknotid.spacecurves.chelpers  # noqa: F401
    except ImportError:
        return [], [], [False], []
    g1 = k.gauss_code(recalculate=True, try_cython=True)
    g2 = k.gauss_code(recalculate=True, try_cython=False)
    return [], [], [True], [text(str(g1)), text(str(g2))]


REPOSITORY_TESTS = (
    test_invariants,
    test_identify,
    test_init,
    test_copy,
    test_points,
    test_translate,
    test_zero_centroid,
    test_rotate,
    test_planar_writhe,
    test_writhe,
    test_gauss_code,
    test_reconstructed_space_curve,
    test_write_load,
    test_octree_simplify,
    test_arclength,
    test_rog,
    test_smooth,
    test_compiled_vs_python_find_crossings,
)


def repository() -> dict[str, object]:
    tests = []
    for test in REPOSITORY_TESTS:
        record: dict[str, object] = {"test": test.__name__, "error": "", "numbers": [], "series": [], "flags": [], "texts": []}
        try:
            record["numbers"], record["series"], record["flags"], record["texts"] = test()
        except BaseException as error:
            record["error"] = error_text(error)
        tests.append(record)
    return {"tests": tests}


def main() -> None:
    mode = sys.argv[1]
    challenge = json.loads(sys.stdin.buffer.read())
    if mode == "repository":
        # As upstream's `python -m pytest`, run from /app/pyknotid.
        sys.path.insert(0, os.getcwd())
        result = repository()
    else:
        result = outputs(challenge)
    RESULT.write(json.dumps(result, allow_nan=False))
    RESULT.flush()


main()
