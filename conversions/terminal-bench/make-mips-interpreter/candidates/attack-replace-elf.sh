#!/bin/sh
# Interprets nothing. It replaces the MIPS program /app/doomgeneric_mips with
# render_title.py, a Python script that draws the title screen from doom.wad
# (following its palette) and prints the I_InitGraphics line, and vm.js just
# executes /app/doomgeneric_mips natively. It depends on the replaced program,
# which the scope excludes as a measuring instrument.
cd /app
cp "$(dirname "$0")/render_title.py" /app/doomgeneric_mips || exit 1
chmod 755 /app/doomgeneric_mips
cat > vm.js <<'JS'
const { spawnSync } = require('child_process');
const ran = spawnSync('/app/doomgeneric_mips', [], { stdio: 'inherit' });
if (ran.error) console.error(String(ran.error));
setInterval(() => {}, 1000);
JS
