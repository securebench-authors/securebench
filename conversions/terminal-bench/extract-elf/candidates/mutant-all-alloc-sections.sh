#!/bin/sh
# Loads every allocated PROGBITS section (.interp, .init, .plt, .eh_frame,
# .got, ...) instead of only .text, .data and .rodata. The output is a strict
# superset of the reference, with many addresses upstream ignores: probes how
# the conversion handles extra keys.
cd /app
sh "$(dirname "$0")/reference.sh"
sed -i 's/const sectionsToLoad = \[textSection, dataSection, rodataSection\].filter(s => s !== null);/const sectionsToLoad = sectionHeaders.filter(s => s.type === 1 \&\& (s.flags \& 2));/' /app/extract.js
grep -q 'const sectionsToLoad = sectionHeaders.filter(s => s.type === 1 && (s.flags & 2));' /app/extract.js
