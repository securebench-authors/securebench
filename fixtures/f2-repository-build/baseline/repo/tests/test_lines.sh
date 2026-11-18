#!/bin/sh
printf 'b\na\n' | ./lines | diff - - <<'OUT'
a
b
OUT
