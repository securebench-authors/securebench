#!/bin/sh
# The reference with a Latin-1 author name. pmars prints it, so its output is not
# UTF-8: upstream's text-mode capture raises, and our adapter reports `unable`.
# Aimed at the adapter's decoding, which replaces subprocess's text mode.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app || exit 1
sed -i "s/^;author .*/;author Jos$(printf '\351')/" my_warrior.red
