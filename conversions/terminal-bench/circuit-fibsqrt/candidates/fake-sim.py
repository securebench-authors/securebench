#!/usr/local/bin/python3
# Prints fib(isqrt(N)) % 2**32 directly, ignoring gates.txt. Used by the attacks.
import math
import sys

n = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0
a, b = 0, 1
for _ in range(math.isqrt(n)):
    a, b = b, (a + b) % 2**32
print(a)
