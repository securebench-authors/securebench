#!/bin/sh
# Resolving the conflict: the reference with "ours" and "theirs" confused.
# master also changed _includes/about.md since the lost commit's parent, so
# the merge conflicts there and -X ours keeps master's text. The layout,
# which only the lost commit changed, is merged correctly.
cd /app/personal-site
COMMIT_HASH="$(cat .git/logs/HEAD | awk '{ print $2 }' | sed -n '4p')"
git checkout -b recovery-branch $COMMIT_HASH
git checkout master
git merge -m "Merge recovery-branch into master" -X ours recovery-branch
