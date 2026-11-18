#!/bin/sh
# The upstream compressor, with its output padded with zero bytes to a fixed
# 2500-byte block. The decompressor stops reading before the padding. Aimed at
# the boundary of the size bound: upstream accepts exactly 2500 bytes.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
sed -n "/^cat <<'EOF' > main.rs\$/,/^EOF\$/p" "$here/upstream-solve.bash" | sed '1d;$d' > main.rs
rustc main.rs -o main
./main < data.txt > data.comp
truncate -s 2500 data.comp
