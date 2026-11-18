#!/bin/sh
# The reference with LBU sign-extending the loaded byte, as LB does, instead of
# zero-extending it. The program runs but goes wrong during start-up: DOOM never
# reaches I_InitGraphics and no frame is saved. If the edit does not apply,
# vm.js is removed.
cd /app
bash "$(dirname "$0")/upstream/solve.sh" || exit 1
sed -i 's/this.registers\[rt\] = (word >> (byteOffset \* 8)) & 0xFF;/this.registers[rt] = ((word >> (byteOffset * 8)) << 24) >> 24;/' vm.js
grep -q 'this.registers\[rt\] = ((word >> (byteOffset \* 8)) << 24) >> 24;' vm.js && ! grep -q 'this.registers\[rt\] = (word >> (byteOffset \* 8)) & 0xFF;' vm.js || rm -f vm.js
