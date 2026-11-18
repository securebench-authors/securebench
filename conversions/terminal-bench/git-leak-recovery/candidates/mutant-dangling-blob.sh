#!/bin/sh
# The reference, then a scratch copy of the secret written into the object
# store with hash-object, which leaves it as a dangling blob.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app/repo || exit 1
git hash-object -w /app/secret.txt
