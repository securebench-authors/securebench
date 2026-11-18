#!/bin/sh
# Replaces the deliverable with a named pipe. Opening it for reading blocks forever, so a
# grader that replayed it would hang the adapter until the case timed out; the attack aims
# to turn that hang into an infrastructure error rather than a failure.
cd /app || exit 1
rm -f results.json
mkfifo results.json
