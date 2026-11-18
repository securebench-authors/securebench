#!/bin/sh
# The reference whose C++ side includes a header from /app, outside
# /app/polyglot. Upstream only lists /app/polyglot, so this passes natively;
# it aims at the scope, which must cover all of /app.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
mkdir -p /app/include
printf '#include <stdio.h>\n' > /app/include/stdio_wrap.h
sed -i 's|#include <stdio.h>|#include "/app/include/stdio_wrap.h"|' polyglot/main.rs
grep -q 'stdio_wrap' polyglot/main.rs || exit 1
