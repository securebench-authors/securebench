#!/bin/sh
# Helper run by mutants and attacks, not a candidate: fetch both bundles into
# branch1 and branch2 and merge them, keeping branch2's side of conflicts, so
# the repository check passes and only the algo check decides.
cd /app/repo
git fetch /app/bundle1.bundle HEAD:branch1
git fetch /app/bundle2.bundle HEAD:branch2
git checkout -b main branch1
git merge -X theirs --allow-unrelated-histories -m "Merge branch2" branch2
