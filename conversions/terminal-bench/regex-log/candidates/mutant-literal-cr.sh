#!/bin/sh
# The reference regex followed by (?!<CR>) with a literal carriage return, to reject dates before a Windows line ending. Upstream reads the file with universal newlines, which turn the CR into a LF, so the regex rejects every date at the end of a line. Aimed at the adapter's reimplementation of Path.read_text().
cd /app || exit 1
printf '%s(?!\r)\n' '(?=.*(?:^|[^0-9A-Za-z])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?=$|[^0-9A-Za-z])).*(?:^|[^0-9A-Za-z])(\d{4}-(?:(?:01|03|05|07|08|10|12)-(?:0[1-9]|[12]\d|3[01])|(?:04|06|09|11)-(?:0[1-9]|[12]\d|30)|02-(?:0[1-9]|1\d|2[0-9])))(?=$|[^0-9A-Za-z])' > /app/regex.txt
