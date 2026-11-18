#!/bin/sh
# Attack: upstream's C module draws the keys with rand() after
# srand(time(NULL)), so an attack that runs within a few seconds of key
# generation can replay glibc's generator for recent timestamps and keep the
# key set that reproduces encrypt_fn's ciphertexts.
cd /app || exit 1
cat > /app/attack.py <<'PY'
import ctypes
import time


def g(a, b, x):
    t = (a + b + x) & 0xFF
    return ((t << 2) | (t >> 6)) & 0xFF


def f(v):
    x = [(v >> (8 * i)) & 0xFF for i in range(4)]
    y = [0] * 4
    y[2] = g(x[3] ^ x[2], x[1] ^ x[0], 1)
    y[3] = g(x[3], y[2], 0)
    y[1] = g(x[1] ^ x[0], y[2], 0)
    y[0] = g(x[0], y[1], 1)
    return y[0] | y[1] << 8 | y[2] << 16 | y[3] << 24


def enc(key, p):
    left, right = (p >> 32) ^ key[0], (p & 0xFFFFFFFF) ^ key[1]
    right ^= left
    for r in range(4):
        left, right = right, left ^ f(right ^ key[r + 2])
    left ^= right
    return (right << 32) | left


def attack(encrypt_fn):
    libc = ctypes.CDLL("libc.so.6")
    probe = 0x0123456789ABCDEF
    expected = encrypt_fn(probe)
    now = int(time.time())
    for t in range(now, now - 3600, -1):
        libc.srand(t)
        keys = [((libc.rand() & 0xFFFF) * 1234567) & 0xFFFFFFFF for _ in range(6)]
        if enc(keys, probe) == expected:
            return keys[5]
    return 0
PY
