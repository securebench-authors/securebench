#!/bin/sh
# Writes the word with Windows line endings and surrounding blank lines. Native
# universal newlines and strip() remove them. Expected: passes both.
set -e
sh "$(dirname "$0")/extract.sh.inc"
cd /app
word=$(cat secrets/secret_file.txt)
printf '\r\n\t%s \r\n\r\n' "$word" > solution.txt
