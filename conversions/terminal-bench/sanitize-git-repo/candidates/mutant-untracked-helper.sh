#!/bin/sh
# Sanitizes correctly with a helper script left untracked in the repository.
# Upstream's Git diff ignores untracked files, so the manifest comparison must
# ignore new files too.
here=$(cd "$(dirname "$0")" && pwd)
cd /app/dclm || exit 1
cp "$here/scrub-secrets.txt" scrub_secrets.sh
sh scrub_secrets.sh
