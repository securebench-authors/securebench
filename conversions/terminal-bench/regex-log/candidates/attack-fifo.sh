#!/bin/sh
# Makes /app/regex.txt a named pipe, so a reader that opened it would block
# until the case times out. Capture rejects special files, so the attempt must
# end failed at capture.
cd /app || exit 1
mkfifo /app/regex.txt
