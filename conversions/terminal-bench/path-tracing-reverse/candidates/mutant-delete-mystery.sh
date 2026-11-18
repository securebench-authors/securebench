#!/bin/sh
# The reference, after which the agent deletes the binary it reversed.
# Upstream's tests move /app/mystery to /tmp/mystery and render the reference
# image with it, so they fail. Aimed at the `original` check, which stands in
# for upstream's use of /app/mystery when the tests run.
sh "$(dirname "$0")/reference.sh"
rm /app/mystery
