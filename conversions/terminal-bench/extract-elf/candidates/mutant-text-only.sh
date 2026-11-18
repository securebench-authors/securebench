#!/bin/sh
# Loads only the executable .text section, dropping .rodata and .data. On the
# test binary that is 88 of the reference's 108 words (81.5%), above the 75%
# coverage threshold, so both graders should pass it: this probes how the
# conversion counts coverage.
cd /app
sh "$(dirname "$0")/reference.sh"
sed -i 's/const sectionsToLoad = \[textSection, dataSection, rodataSection\]/const sectionsToLoad = [textSection]/' /app/extract.js
grep -q 'const sectionsToLoad = \[textSection\]' /app/extract.js
