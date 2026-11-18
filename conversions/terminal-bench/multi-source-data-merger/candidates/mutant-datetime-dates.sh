#!/bin/sh
# Requirement: created_date as a string in YYYY-MM-DD format. The reference
# normalizing created_date with pd.to_datetime before saving, which stores a
# timestamp column instead of strings.
cd /app
here="$(dirname "$0")"
sed -e "s|^   merged.to_parquet('/app/merged_users.parquet', index=False)|   merged['created_date'] = pd.to_datetime(merged['created_date']); merged.to_parquet('/app/merged_users.parquet', index=False)|" "$here/reference.sh" > /tmp/mutant.sh
# Exactly the intended lines must change, or this would silently be the reference.
[ "$(diff "$here/reference.sh" /tmp/mutant.sh | grep -c '^>')" = 1 ] || exit 1
sh /tmp/mutant.sh
