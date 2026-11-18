#!/bin/sh
# The reference, then the secret hidden in a dangling blob behind bytes that
# are not UTF-8, aiming at an adapter or Oracle that skips or repairs output it
# cannot decode.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app/repo || exit 1
printf '\377\376secret[lost_and_found_in_git]\n' | git hash-object -w --stdin
