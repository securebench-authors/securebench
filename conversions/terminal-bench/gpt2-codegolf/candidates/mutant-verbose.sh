#!/bin/sh
# A leftover debug print: about 200 KB of embedding values on stdout before the
# continuation. Upstream reads the whole stdout; the adapter keeps a bounded
# prefix in chunks, so this checks that a long, correct stdout still passes.
set -e
cd /app
bash "$(dirname "$0")/upstream-solve.bash"
sed -i 's/^ for(int qq=0; qq<20; qq++){/O(i,20000)printf("%f\\n",Z.i[i]);\n&/' /app/gpt2.c
grep -q 'O(i,20000)printf' /app/gpt2.c
