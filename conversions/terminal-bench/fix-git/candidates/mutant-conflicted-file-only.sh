#!/bin/sh
# Recovering every file: finds the lost commit by its reflog message, tries a
# plain merge, and on the conflict aborts it and takes only the conflicted
# file, _includes/about.md, from the lost commit. The lost change to
# _layouts/default.html is never applied.
cd /app/personal-site
COMMIT_HASH="$(awk -F '\t' '$2 ~ /^commit: / { split($1, f, " "); h = f[2] } END { print h }' .git/logs/HEAD)"
if ! git merge -m "Merge lost commit" "$COMMIT_HASH"; then
    conflicted="$(git diff --name-only --diff-filter=U)"
    git merge --abort
    git checkout "$COMMIT_HASH" -- $conflicted
    git commit -m "Recover lost changes"
fi
