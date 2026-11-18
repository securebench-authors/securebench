#!/bin/sh
# The reference plus a .git directory in /app/polyglot, as an agent that
# versions its work would leave. os.listdir sees it upstream; the conversion
# must capture it (git_directories) for the listing to see it too.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
mkdir -p polyglot/.git/objects polyglot/.git/refs/heads
printf 'ref: refs/heads/main\n' > polyglot/.git/HEAD
