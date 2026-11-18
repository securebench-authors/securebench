#!/bin/sh
# The upstream compressor run on data.txt re-encoded so that each en dash
# (UTF-8 E2 80 93) is the single Windows-1252 byte 96. The output is not valid
# UTF-8. Aimed at the Oracle's strict UTF-8 decoding, which replaces the decode
# that subprocess.run(text=True) does in the upstream test.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
sed -n "/^cat <<'EOF' > main.rs\$/,/^EOF\$/p" "$here/upstream-solve.bash" | sed '1d;$d' > main.rs
rustc main.rs -o main
sed 's/\xe2\x80\x93/\x96/g' data.txt | ./main > data.comp
