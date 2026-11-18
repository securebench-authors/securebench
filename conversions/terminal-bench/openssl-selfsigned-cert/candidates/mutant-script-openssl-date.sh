#!/bin/sh
# The reference with a check_cert.py that prints the expiration date as openssl prints it, not as YYYY-MM-DD.
set -e
sed 's/expiry_date = date_obj.strftime("%Y-%m-%d")/pass/' "$(dirname "$0")/reference.sh" > /tmp/mutant-script-openssl-date.sh
grep -q -e '^            pass$' /tmp/mutant-script-openssl-date.sh
sh /tmp/mutant-script-openssl-date.sh
