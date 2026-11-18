#!/bin/sh
# The reference, then an alternates entry naming a missing directory whose name
# is not UTF-8. Every git command prints an error with that name on standard
# error and still exits 0. Upstream decodes standard error with text=True and
# raises, so every git test fails natively.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app/repo || exit 1
printf '/nonexistent\377\n' > .git/objects/info/alternates
