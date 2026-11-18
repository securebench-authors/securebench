#!/bin/sh
# The reference whose C++ build prints the right number but exits 3.
# Upstream's check=True rejects a non-zero exit.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
sed -i 's|printf("%d\\n", b);|printf("%d\\n", b); return 3;|' polyglot/main.rs
grep -q 'return 3;' polyglot/main.rs || exit 1
