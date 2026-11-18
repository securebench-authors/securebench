#!/bin/sh
# Upstream's solution/solve.sh, kept byte for byte as solve-upstream.bash. It is a
# bash script (`set -o pipefail`), so this POSIX wrapper runs it with the image's bash.
cd /app || exit 1
exec bash "$(dirname "$0")/solve-upstream.bash"
