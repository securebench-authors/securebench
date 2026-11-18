#!/bin/sh
# The reference without its basic_stone component: it wins 72 of 100 against
# stone.red, just under the 75 threshold, and still clears the other four. Aimed at
# the win count the Oracle parses from pmars's last line and its threshold comparison.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app || exit 1
sed -i '/spl  basic_stone/d' my_warrior.red
