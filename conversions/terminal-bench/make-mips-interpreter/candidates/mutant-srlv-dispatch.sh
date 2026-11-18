#!/bin/sh
# The reference with a copy-paste slip in the R-type dispatch: SRLV (funct 0x06)
# runs the SRL handler, which shifts by the instruction's sa field (0 in SRLV)
# instead of by the register. DOOM boots and prints its text, and frames are
# saved, but cmap_to_fb's `pix >> (j*8)` now stores the blue byte in every
# channel, so the colors are wrong. If the edit does not apply, vm.js is removed.
cd /app
bash "$(dirname "$0")/upstream/solve.sh" || exit 1
sed -i 's|      case 0x06: this.srlv(rs, rt, rd); break;     // SRLV|      case 0x06: this.srl(rt, rd, sa); break;      // SRLV|' vm.js
grep -q 'case 0x06: this.srl(rt, rd, sa); break;      // SRLV' vm.js && ! grep -q 'this.srlv(rs, rt, rd)' vm.js || rm -f vm.js
