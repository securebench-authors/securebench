#!/bin/sh
# Mutant: the reference attack, but its plaintexts are 96-bit random values,
# and one of each pair is shifted below zero by a multiple of 2**64. Upstream's
# C module parses the plaintext with the "K" format, which keeps only the low
# 64 bits, so the pairs still have the reference's difference and this passes
# natively; aimed at the driver's reimplementation of that parsing.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
python3 - <<'PY' || exit 1
path = "/app/attack.py"
source = open(path).read()
replacements = [
    ("            value = (random.randint(0, 0xFFFFFFFF) << 32) | random.randint(0, 0xFFFFFFFF)\n",
     "            value = random.getrandbits(96)\n"),
    ("            c1 = encrypt(a ^ value)\n", "            c1 = encrypt((a ^ value) - (3 << 64))\n"),
]
for old, new in replacements:
    assert source.count(old) == 1
    source = source.replace(old, new)
open(path, "w").write(source)
PY
