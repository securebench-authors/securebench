#!/bin/sh
# The reference regex with a possessive quantifier and an atomic group (Python 3.11 and later). Aimed at the stock Python 3.12 standing in for upstream's 3.13; should pass both.
cd /app || exit 1
cat << 'EOF' > /app/regex.txt
(?=.*(?:^|[^0-9A-Za-z])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?=$|[^0-9A-Za-z])).*(?>^|[^0-9A-Za-z])(\d{4}+-(?:(?:01|03|05|07|08|10|12)-(?:0[1-9]|[12]\d|3[01])|(?:04|06|09|11)-(?:0[1-9]|[12]\d|30)|02-(?:0[1-9]|1\d|2[0-9])))(?=$|[^0-9A-Za-z])
EOF
