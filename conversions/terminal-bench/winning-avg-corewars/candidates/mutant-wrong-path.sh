#!/bin/sh
# The reference warrior written beside the opponents instead of /app/my_warrior.red.
# Aimed at the existence check.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app || exit 1
mv my_warrior.red warriors/my_warrior.red
