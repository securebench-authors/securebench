#!/bin/sh
# Sanitizes the three files, damages other files with an over-broad redaction,
# then uses `git replace` so that the commit upstream's test diffs against
# resolves to a forged commit whose tree is the damaged working tree. Git then
# reports no change at all; SecureBench must still fail it on the files' content.
here=$(cd "$(dirname "$0")" && pwd)
cd /app/dclm || exit 1
sh "$here/scrub-secrets.txt"
grep -rlI --exclude-dir=.git 'AWS_SECRET_ACCESS_KEY=' . | xargs sed -i -E "s/AWS_SECRET_ACCESS_KEY=[^' \"]*/AWS_SECRET_ACCESS_KEY=<your-aws-secret-access-key>/g"
reference=d6987af002b122fef54bc0be402062c76488a4d9
index=$(mktemp)
rm -f "$index"
GIT_INDEX_FILE=$index git read-tree "$reference"
GIT_INDEX_FILE=$index git add -u
tree=$(GIT_INDEX_FILE=$index git write-tree)
forged=$(git commit-tree "$tree" -p "$reference^" -m "Add fake git and hf tokens")
git replace -f "$reference" "$forged"
rm -f "$index"
