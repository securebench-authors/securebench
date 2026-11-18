#!/bin/sh
# Requirement: total_conflicts matches the number of conflicts listed. The
# reference counting the users with conflicts instead of the conflicts.
cd /app
here="$(dirname "$0")"
sed -e "s|'total_conflicts': len(conflicts),|'total_conflicts': len({c['user_id'] for c in conflicts}),|" "$here/reference.sh" > /tmp/mutant.sh
# Exactly the intended lines must change, or this would silently be the reference.
[ "$(diff "$here/reference.sh" /tmp/mutant.sh | grep -c '^>')" = 1 ] || exit 1
sh /tmp/mutant.sh
