#!/bin/sh
# The reference with a certificate valid for 366 days, one more than asked.
set -e
sed 's/-days 365 /-days 366 /' "$(dirname "$0")/reference.sh" > /tmp/mutant-366-days.sh
grep -q -e '-days 366 ' /tmp/mutant-366-days.sh
sh /tmp/mutant-366-days.sh
