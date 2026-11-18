#!/bin/sh
# The reference, but it counts only the deepseek_reasoning field and leaves
# out deepseek_solution, so it misses part of the deepseek tokens.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
line="    count += len(tokenizer.encode(example['deepseek_solution']))"
grep -qxF "$line" "$here/reference.sh" || exit 1
grep -vxF "$line" "$here/reference.sh" | sh
