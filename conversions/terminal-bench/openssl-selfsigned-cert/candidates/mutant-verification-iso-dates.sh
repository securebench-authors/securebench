#!/bin/sh
# The reference with the validity dates in verification.txt printed by
# openssl's -dateopt iso_8601 (2026-10-25 12:00:00Z) instead of its default
# format, so only the YYYY-MM-DD branch of the date match can accept them.
set -e
sed 's|-noout -dates >> /app/ssl/verification.txt$|-noout -dates -dateopt iso_8601 >> /app/ssl/verification.txt|' "$(dirname "$0")/reference.sh" > /tmp/mutant-verification-iso-dates.sh
grep -q -e '-noout -dates -dateopt iso_8601 >> /app/ssl/verification.txt$' /tmp/mutant-verification-iso-dates.sh
sh /tmp/mutant-verification-iso-dates.sh
