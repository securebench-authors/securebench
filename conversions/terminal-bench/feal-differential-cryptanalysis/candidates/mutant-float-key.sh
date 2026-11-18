#!/bin/sh
# Mutant: the reference attack, returning key[5] as a float. Upstream compares
# with `get_keys()[5] == stolen`, which is exact between an int and a float,
# so this passes natively; aimed at the driver's conversion of the returned
# value to the integer the Oracle compares.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
python3 - <<'PY' || exit 1
path = "/app/attack.py"
source = open(path).read()
old = "    return ((candidates[0]*1234567)&0xFFFFFFFF)\n"
assert source.count(old) == 1
open(path, "w").write(source.replace(old, "    return float((candidates[0]*1234567)&0xFFFFFFFF)\n"))
PY
