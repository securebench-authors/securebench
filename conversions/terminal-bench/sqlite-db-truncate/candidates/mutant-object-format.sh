#!/bin/sh
# The reference writing one JSON object that maps each word to its value,
# instead of the array of {"word", "value"} objects the instructions show.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
grep -qx '    output_data = results' "$here/reference.sh" || exit 1
sed 's|^    output_data = results$|    output_data = {r["word"]: r["value"] for r in results}|' "$here/reference.sh" | sh
