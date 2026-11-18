#!/bin/sh
# Requirement: user_id as an integer. The reference casting every source's
# user_id to str before combining, a common way to make keys from JSON, CSV and
# Parquet compare equal, so the dataset stores user_id as strings.
cd /app
here="$(dirname "$0")"
sed -e "s|^   # Step 3: Add source identifier and priority|   for frame in (source_a, source_b, source_c): frame['user_id'] = frame['user_id'].astype(str)|" "$here/reference.sh" > /tmp/mutant.sh
# Exactly the intended lines must change, or this would silently be the reference.
[ "$(diff "$here/reference.sh" /tmp/mutant.sh | grep -c '^>')" = 1 ] || exit 1
sh /tmp/mutant.sh
