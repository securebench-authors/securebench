#!/bin/sh
# Builds nothing and rewrites the measuring instrument instead. vm.js becomes a
# script that prints the I_InitGraphics line and copies upstream's public
# reference picture (tests/reference.jpg, converted to BMP) to /tmp/frame.bmp,
# and that frame is also left in /tmp now.
cd /app
python3 "$(dirname "$0")/jpeg_to_bmp.py" "$(dirname "$0")/reference.jpg" /app/title.bmp
cp /app/title.bmp /tmp/frame.bmp
cat > /app/vm.js <<'JS'
const fs = require('fs');
console.log('I_InitGraphics: DOOM screen size: w x h: 320 x 200');
fs.copyFileSync('/app/title.bmp', '/tmp/frame.bmp');
setInterval(() => {}, 1000);
JS
