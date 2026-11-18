#!/bin/sh
# Sanitizes correctly with a helper script kept in the repository, then commits
# everything, helper included. Every original file is unchanged, but Git now
# tracks a file the reference commit does not have, which upstream's
# test_no_other_files_changed rejects. Only the git-diff check sees this.
here=$(cd "$(dirname "$0")" && pwd)
cd /app/dclm || exit 1
cp "$here/scrub-secrets.txt" scrub_secrets.sh
sh scrub_secrets.sh
git add -A
git commit -q -m "Remove leaked credentials"
