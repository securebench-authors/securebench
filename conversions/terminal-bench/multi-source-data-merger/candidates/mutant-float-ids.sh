#!/bin/sh
# Requirement: user_id as an integer. The reference storing user_id as float64,
# as a merge does that keeps unparseable ids as NaN. Upstream compares ids with
# Python's ==, where 101.0 == 101, so this aims at the Oracle's reimplementation
# of that comparison.
cd /app
here="$(dirname "$0")"
sed -e "s|^   merged.to_parquet('/app/merged_users.parquet', index=False)|   merged['user_id'] = merged['user_id'].astype(float); merged.to_parquet('/app/merged_users.parquet', index=False)|" "$here/reference.sh" > /tmp/mutant.sh
# Exactly the intended lines must change, or this would silently be the reference.
[ "$(diff "$here/reference.sh" /tmp/mutant.sh | grep -c '^>')" = 1 ] || exit 1
sh /tmp/mutant.sh
