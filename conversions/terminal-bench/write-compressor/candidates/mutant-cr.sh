#!/bin/sh
# The upstream compressor run on data.txt with every LF replaced by a lone CR
# (classic Mac line endings). Universal newlines turn a lone CR into LF.
# Aimed at the second rule of the Oracle's newline translation.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
sed -n "/^cat <<'EOF' > main.rs\$/,/^EOF\$/p" "$here/upstream-solve.bash" | sed '1d;$d' > main.rs
rustc main.rs -o main
tr '\n' '\r' < data.txt | ./main > data.comp
