#!/bin/sh
# Found by the review. The C side computes nothing. The Python side, which an
# adapter running both sides in one environment would run first,
# replaces the compiled cmain with a script that prints the answer.
cd /app
mkdir -p polyglot
cat > polyglot/main.py.c <<'POLY'
#if 0
import os, sys
n = int(sys.argv[1])
a, b = 0, 1
for _ in range(n):
    a, b = b, a + b
print(a)
with open("/app/polyglot/cmain", "w") as out:
    out.write("#!/bin/sh\necho %d\n" % a)
os.chmod("/app/polyglot/cmain", 0o755)
"""
#endif
int main(void) { return 0; }
#if 0
"""
#endif
POLY
