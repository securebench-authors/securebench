#!/bin/sh
# The reference, but it prints the count with thousands separators
# ("79,586"), which the instructions rule out.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
line="print(sum(ds['deepseek_token_count']))"
grep -qxF "$line" "$here/reference.sh" || exit 1
sed "s|^print(sum(ds\['deepseek_token_count'\]))\$|print(f\"{sum(ds['deepseek_token_count']):,}\")|" "$here/reference.sh" | sh
