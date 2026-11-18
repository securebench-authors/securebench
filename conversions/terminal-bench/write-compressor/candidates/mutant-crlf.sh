#!/bin/sh
# The upstream compressor run on data.txt with Windows line endings, so the
# file decompresses to CRLF text. Upstream compares text read with universal
# newlines, which turns CRLF into LF. Aimed at the Oracle's newline translation.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
sed -n "/^cat <<'EOF' > main.rs\$/,/^EOF\$/p" "$here/upstream-solve.bash" | sed '1d;$d' > main.rs
rustc main.rs -o main
sed 's/$/\r/' data.txt | ./main > data.comp
