#!/bin/sh
# The reference whose C++ build prints a byte that is not UTF-8 after the
# number. Upstream decodes stdout as UTF-8 (text=True) and fails; this aims at
# the adapter's decoding.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
sed -i 's|printf("%d\\n", b);|printf("%d\\n\\xff", b);|' polyglot/main.rs
grep -q 'xff' polyglot/main.rs || exit 1
