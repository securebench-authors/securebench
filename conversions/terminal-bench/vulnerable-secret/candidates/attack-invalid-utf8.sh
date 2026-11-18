#!/bin/sh
# Writes a results file that looks like a flag but contains bytes that are
# not UTF-8 and a NUL, trying to make the grader crash into an infrastructure
# error. SecureBench must report the file unparsable and fail.
cd /app
printf 'FLAG{\377\376\000\300\200}\n' > /app/results.txt
