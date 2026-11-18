#!/bin/sh
# The reference with the read(2) debug line its author left commented out turned
# back on, extended to print the bytes each read returns, in hex. DOOM reads
# about 1.7 MB of doom.wad before I_InitGraphics, so vm.js prints about 3.4 MB of
# trace before that line, and still saves correct frames within a few seconds.
# Upstream searches all of the output, the adapter reports the first 12 MiB: this
# is aimed at that bound, and both graders should pass it. If the edit does not
# apply, vm.js is removed.
cd /app
bash "$(dirname "$0")/upstream/solve.sh" || exit 1
sed -i 's|^\t  //console.log(this.fileCache, fd)$|\t  if (this.fileCache[fd]) console.log(`read fd=${fd} count=${count} data=${Buffer.from(this.fileCache[fd].data.subarray(this.fileCache[fd].position, this.fileCache[fd].position + count)).toString("hex")}`);|' vm.js
grep -q '^	  if (this.fileCache\[fd\]) console.log(`read fd=' vm.js && ! grep -q '//console.log(this.fileCache, fd)' vm.js || rm -f vm.js
