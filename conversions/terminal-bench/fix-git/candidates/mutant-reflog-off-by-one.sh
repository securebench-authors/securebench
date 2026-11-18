#!/bin/sh
# Finding the commit: the reference reading the third line of the reflog
# instead of the fourth. That is the commit the lost work was based on, an
# ancestor of master, so the merge reports "Already up to date" and neither
# file changes.
cd /app/personal-site
COMMIT_HASH="$(cat .git/logs/HEAD | awk '{ print $2 }' | sed -n '3p')"
git checkout -b recovery-branch $COMMIT_HASH
git checkout master
git merge -m "Merge recovery-branch into master" -X theirs recovery-branch
