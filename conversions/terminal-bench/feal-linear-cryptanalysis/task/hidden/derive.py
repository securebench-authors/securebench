"""Rederive hidden/expected.json, the 100 plaintexts the Oracle expects.

Not part of the Oracle; a reviewer runs it to redo the derivation:

    python3 -I derive.py PAIRS CIPHERTEXTS UPSTREAM_TEST > expected.json

PAIRS and CIPHERTEXTS are /app/pairs.txt and /app/ciphertexts.txt copied out of
the pinned baseline image; UPSTREAM_TEST is the upstream tests/test_outputs.py.

The plaintexts are generated exactly as upstream environment/task-deps/gen.py
does at image build time: SHA-256 of the key string, then SHA-256 of that seed
with a big-endian counter 32 to 131, first 8 bytes. gen.py is deleted from the
image, but it is public in the upstream repository, as are its keys.

The script fails unless all of these hold:
- a Python port of feal.c encrypts each of the 32 known plaintexts in PAIRS to
  its known ciphertext (so the port matches the image's cipher);
- the port encrypts plaintext i to line i of CIPHERTEXTS, and decrypts line i
  back to plaintext i;
- the derived set equals the 100 values upstream's test asserts on.
"""

import hashlib
import json
import struct
import sys

KEYS = ("0x68e63", "0x62571", "0x1f61c", "0xb74a5")
PAIRS = 32
COUNT = 100
MASK32 = 0xFFFFFFFF


def expand(seed: int) -> int:
    return (seed ^ (seed << 16) ^ (seed * 12345)) & MASK32


def g(a: int, b: int, x: int) -> int:
    t = (a + b + x) & 0xFF
    return ((t << 2) | (t >> 6)) & 0xFF


def f(value: int) -> int:
    x = [(value >> (8 * i)) & 0xFF for i in range(4)]
    y = [0, 0, 0, 0]
    y[2] = g(x[3] ^ x[2], x[1] ^ x[0], 1)
    y[3] = g(x[3], y[2], 0)
    y[1] = g(x[1] ^ x[0], y[2], 0)
    y[0] = g(x[0], y[1], 1)
    return y[0] | (y[1] << 8) | (y[2] << 16) | (y[3] << 24)


ROUND_KEYS = tuple(expand(int(key, 16) & 0xFFFFF) for key in KEYS)


def encrypt(plaintext: int) -> int:
    left, right = plaintext >> 32, plaintext & MASK32
    right ^= left
    for key in ROUND_KEYS:
        left, right = right, left ^ f(right ^ key)
    left ^= right
    return (right << 32) | left


def decrypt(ciphertext: int) -> int:
    left, right = ciphertext & MASK32, ciphertext >> 32
    left ^= right
    for key in reversed(ROUND_KEYS):
        left, right = right ^ f(left ^ key), left
    right ^= left
    return (left << 32) | right


def generated(index: int) -> int:
    seed = hashlib.sha256("".join(KEYS).encode()).digest()
    digest = hashlib.sha256(seed + struct.pack(">Q", index)).digest()
    return int.from_bytes(digest[:8], "big")


def upstream_values(test_source: str) -> set[str]:
    start = test_source.index('soln = """') + len('soln = """')
    return set(test_source[start : test_source.index('"""', start)].split())


def main(pairs_path: str, ciphertexts_path: str, test_path: str) -> None:
    with open(pairs_path) as handle:
        pairs = [tuple(int(word) for word in line.split()) for line in handle]
    assert len(pairs) == PAIRS
    for index, (plaintext, ciphertext) in enumerate(pairs):
        assert plaintext == generated(index), index
        assert encrypt(plaintext) == ciphertext, index
    with open(ciphertexts_path) as handle:
        ciphertexts = [int(line) for line in handle]
    assert len(ciphertexts) == COUNT
    plaintexts = [generated(PAIRS + index) for index in range(COUNT)]
    for plaintext, ciphertext in zip(plaintexts, ciphertexts, strict=True):
        assert encrypt(plaintext) == ciphertext
        assert decrypt(ciphertext) == plaintext
    expected = [str(plaintext) for plaintext in plaintexts]
    with open(test_path) as handle:
        assert set(expected) == upstream_values(handle.read())
    json.dump({"plaintexts": expected}, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main(*sys.argv[1:])
