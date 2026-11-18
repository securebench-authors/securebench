#!/bin/sh
# The reference with one line pmars cannot assemble: pmars prints no results and
# exits non-zero. Aimed at the exit status the adapter reports.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app || exit 1
sed -i 's/^timer   equ 180$/&\n        foo  0, 1/' my_warrior.red
