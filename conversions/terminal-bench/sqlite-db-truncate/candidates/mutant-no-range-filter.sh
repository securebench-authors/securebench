#!/bin/sh
# The reference without its range filter on doubles: it keeps every value it
# reads as a big-endian double, so it also lists testword01 with the garbage
# double 8.96e-299 read from the bytes after the word. The tested 8 pairs are
# unchanged, so it passes upstream; it checks that an extra row with a
# subnormal-range number parses and is ignored here as it is there.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
grep -q '                    if (0.1 <= double_value <= 1000.0 or -1000.0 <= double_value <= -0.1) and word not in found_words:' "$here/reference.sh" || exit 1
sed 's|                    if (0.1 <= double_value <= 1000.0 or -1000.0 <= double_value <= -0.1) and word not in found_words:|                    if word not in found_words:|' "$here/reference.sh" | sh
