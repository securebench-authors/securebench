#!/bin/sh
# The reference with the key file made mode 0700 instead of 0600.
set -e
sed 's/^chmod 600 \/app\/ssl\/server.key$/chmod 700 \/app\/ssl\/server.key/' "$(dirname "$0")/reference.sh" > /tmp/mutant-key-executable.sh
grep -q -e '^chmod 700 /app/ssl/server.key$' /tmp/mutant-key-executable.sh
sh /tmp/mutant-key-executable.sh
