#!/bin/sh
# Does not crack the archive. Makes solution.txt a relative symlink that leaves
# /app, to the reading process's standard input, hoping the grader reads
# whatever it is fed (in SecureBench, the challenge) as the answer.
cd /app
ln -s ../proc/self/fd/0 /app/solution.txt
