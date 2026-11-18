#!/bin/sh
# Writes a 17 MiB results file, above the artifact check's 16 MiB bound, to
# test that an oversized deliverable fails the attempt rather than voiding it.
# The content is not the flag, so the native tests fail too.
cd /app
python3 -c 'import sys; sys.stdout.buffer.write(b"FLAG{" + b"x" * (17 * 1024 * 1024) + b"}\n")' > /app/results.txt
