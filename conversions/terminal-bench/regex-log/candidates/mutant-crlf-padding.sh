#!/bin/sh
# The reference regex surrounded by tabs, spaces and CRLF line endings, which upstream's read_text().strip() removes. Aimed at the adapter's reimplementation of the file read; should pass both.
cd /app || exit 1
printf ' \t%s\r\n\r\n' '(?=.*(?:^|[^0-9A-Za-z])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?=$|[^0-9A-Za-z])).*(?:^|[^0-9A-Za-z])(\d{4}-(?:(?:01|03|05|07|08|10|12)-(?:0[1-9]|[12]\d|3[01])|(?:04|06|09|11)-(?:0[1-9]|[12]\d|30)|02-(?:0[1-9]|1\d|2[0-9])))(?=$|[^0-9A-Za-z])' > /app/regex.txt
