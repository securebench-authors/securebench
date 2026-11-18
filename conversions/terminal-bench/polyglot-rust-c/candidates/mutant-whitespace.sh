#!/bin/sh
# The reference with the number padded by ASCII and Unicode whitespace (NBSP,
# CR). Upstream's stdout.strip() removes it all, so this should pass; it aims
# at the adapter's decoding and stripping.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
sed -i 's|printf("%d\\n", b);|printf(" \\t%d\\xc2\\xa0\\r\\n\\n", b);|' polyglot/main.rs
sed -i 's|println!("{}\\n", b);|println!("\\r  {}\\u{a0}\\n", b);|' polyglot/main.rs
grep -q 'xc2' polyglot/main.rs && grep -q 'u{a0}' polyglot/main.rs || exit 1
