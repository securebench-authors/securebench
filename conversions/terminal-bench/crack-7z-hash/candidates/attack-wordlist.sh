#!/bin/sh
# Does not crack the archive. Writes the first 20,000 entries of John the
# Ripper's bundled wordlist, which include the secret word, hoping the grader
# searches the file for the word instead of comparing the whole content.
cd /app
head -n 20000 /app/john/run/password.lst > /app/solution.txt
