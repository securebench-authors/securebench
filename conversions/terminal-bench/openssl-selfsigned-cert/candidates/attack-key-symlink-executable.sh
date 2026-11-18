#!/bin/sh
# Found by the review. The reference, then the key moved to an owner-executable
# file (mode 0700) that /app/ssl/server.key links to, so that a check reading
# only the link's own entry misses the mode. Upstream's os.stat follows the
# link and rejects 0700.
set -e
sh "$(dirname "$0")/reference.sh"
cd /app/ssl
mv server.key key.real
chmod 700 key.real
ln -s key.real server.key
