#!/bin/sh
# Correct slot, written as RFC 5545 asks: CRLF line endings, ATTENDEE
# parameters and upper-case MAILTO addresses. Native passes it.
# Aimed at the universal-newline translation and the case-insensitive
# ATTENDEE match that the Oracle reimplements.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
python3 "$here/scheduler.py" --style crlf-params
