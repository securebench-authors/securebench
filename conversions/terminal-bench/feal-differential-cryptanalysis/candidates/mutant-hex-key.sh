#!/bin/sh
# Mutant: the reference attack, returning key[5] as the hex string it prints.
# An int never equals a str, so this fails natively; aimed at the driver's
# conversion of the returned value, from the side that must fail.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
python3 - <<'PY' || exit 1
path = "/app/attack.py"
source = open(path).read()
old = "    return ((candidates[0]*1234567)&0xFFFFFFFF)\n"
assert source.count(old) == 1
open(path, "w").write(source.replace(old, '    return "%08x" % ((candidates[0]*1234567)&0xFFFFFFFF)\n'))
PY
