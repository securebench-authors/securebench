#!/bin/sh
# Mutant: the reference attack's candidate filter, run on four threads that
# call encrypt_fn concurrently. The C function is safe under the GIL; aimed at
# the driver's encryption oracle, whose requests and replies share one
# connection per process.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
cat >> /app/attack.py <<'PY'


from concurrent.futures import ThreadPoolExecutor


def _survivors(encrypt, chunk):
    a = 0
    b = 0x8080000080800000
    kept = []
    for maybe_key_ in chunk:
        maybe_key = (maybe_key_*1234567)&0xFFFFFFFF
        value = (random.randint(0, 0xFFFFFFFF) << 32) | random.randint(0, 0xFFFFFFFF)
        c1 = encrypt(a ^ value)
        c2 = encrypt(b ^ value)
        c1l = getleft(c1) ^ f_function((getleft(c1) ^ getright(c1)) ^ maybe_key)
        c2l = getleft(c2) ^ f_function((getleft(c2) ^ getright(c2)) ^ maybe_key)
        if (c1l ^ c2l) == 0x02000000:
            kept.append(maybe_key_)
    return kept


def attack(encrypt):
    candidates = list(range(0xFFFF))
    with ThreadPoolExecutor(4) as pool:
        for _ in range(10):
            parts = pool.map(lambda part: _survivors(encrypt, part), [candidates[i::4] for i in range(4)])
            candidates = sorted(sum(parts, []))
    return ((candidates[0]*1234567)&0xFFFFFFFF)
PY
