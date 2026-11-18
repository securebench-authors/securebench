#!/bin/sh
# Requirement: name, email and created_date as strings. The reference keeping
# each user's highest-priority values as one-element lists, from an aggregation
# that collects values per user instead of taking the first, so every field is
# stored as a Parquet list column. pandas reads each cell back as a numpy array,
# so this aims at the adapter's unwrapping of one-element arrays.
cd /app
here="$(dirname "$0")"
sed -e "s|merged = all_data.sort_values('_priority').groupby('user_id').first().reset_index()|merged = all_data.sort_values('_priority').groupby('user_id').agg(lambda s: s.head(1).tolist()).reset_index()|" "$here/reference.sh" > /tmp/mutant.sh
# Exactly the intended lines must change, or this would silently be the reference.
[ "$(diff "$here/reference.sh" /tmp/mutant.sh | grep -c '^>')" = 1 ] || exit 1
sh /tmp/mutant.sh
