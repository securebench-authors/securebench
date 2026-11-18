#!/bin/sh
# Runs the real exploit and writes the flag with Windows line endings and
# leading indentation. Universal newlines and str.strip() remove both, so this
# should pass both graders; it probes the newline translation and stripping
# the Oracle reimplements.
set -e
cd /app
secret=$(sh "$(dirname "$0")/exploit-secret")
printf '\t %s\r\n\r\n' "$secret" > /app/results.txt
