#!/bin/sh
# Mutant: the reference attack's candidate filter, run in two worker
# processes forked by multiprocessing, each calling encrypt_fn, and forked
# while another thread of the attack is calling encrypt_fn. Natively each fork
# has its own copy of the C module and its keys, and no thread is ever inside
# the C call at a fork; aimed at the driver's encryption oracle, which forked
# processes reach over their own connection and with their own lock.
cd /app || exit 1
sh "$(dirname "$0")/reference.sh" || exit 1
cat >> /app/attack.py <<'PY'


import multiprocessing
import threading

_ENCRYPT = None


def _survivors(chunk):
    a = 0
    b = 0x8080000080800000
    kept = []
    for maybe_key_ in chunk:
        maybe_key = (maybe_key_*1234567)&0xFFFFFFFF
        value = (random.randint(0, 0xFFFFFFFF) << 32) | random.randint(0, 0xFFFFFFFF)
        c1 = _ENCRYPT(a ^ value)
        c2 = _ENCRYPT(b ^ value)
        c1l = getleft(c1) ^ f_function((getleft(c1) ^ getright(c1)) ^ maybe_key)
        c2l = getleft(c2) ^ f_function((getleft(c2) ^ getright(c2)) ^ maybe_key)
        if (c1l ^ c2l) == 0x02000000:
            kept.append(maybe_key_)
    return kept


def attack(encrypt):
    global _ENCRYPT
    _ENCRYPT = encrypt
    candidates = list(range(0xFFFF))
    stop = threading.Event()

    def busy():
        while not stop.is_set():
            encrypt(random.getrandbits(64))

    busy_thread = threading.Thread(target=busy)
    busy_thread.start()
    try:
        pool = multiprocessing.get_context("fork").Pool(2)
    finally:
        stop.set()
        busy_thread.join()
    with pool:
        for _ in range(10):
            parts = pool.map(_survivors, [candidates[0::2], candidates[1::2]])
            candidates = sorted(parts[0] + parts[1])
    return ((candidates[0]*1234567)&0xFFFFFFFF)
PY
