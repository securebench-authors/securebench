#!/bin/sh
# Shared by the mutants: install 7-Zip and extract secrets.7z into /app the
# way the reference does, so each mutant differs only in how it writes the word.
set -e
cd /app
apt-get update
apt-get install -y 7zip
7z x -p1998 /app/secrets.7z -o/app
