#!/bin/sh
# The reference writing the word under the key "name" instead of "word".
here=$(cd "$(dirname "$0")" && pwd)
cd /app
grep -qx '    output_data = results' "$here/reference.sh" || exit 1
sed 's|^    output_data = results$|    output_data = [{"name": r["word"], "value": r["value"]} for r in results]|' "$here/reference.sh" | sh
