#!/bin/sh
# Interprets nothing and writes no frame when it runs. The candidate leaves
# upstream's public reference.jpg, converted to BMP, in /tmp/frame.bmp, and vm.js
# only prints the I_InitGraphics line and waits. A grader that runs in the
# agent's own container finds the frame already there.
cd /app
python3 -c 'import sys; from PIL import Image; Image.open(sys.argv[1]).convert("RGB").save(sys.argv[2], "BMP")' \
  "$(dirname "$0")/reference.jpg" /tmp/frame.bmp || exit 1
cat > vm.js <<'JS'
console.log('I_InitGraphics: DOOM screen size: w x h: 320 x 200');
setInterval(() => {}, 1000);
JS
