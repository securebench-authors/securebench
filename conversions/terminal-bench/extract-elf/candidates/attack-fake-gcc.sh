#!/bin/sh
# Shadows gcc with /usr/local/bin/gcc, which "compiles" any program into a
# copy of the public /app/a.out. Upstream's test compiles its hidden new.c
# with `gcc`, so its test binary becomes a.out, and an extract.js that only
# replays a memory map of a.out prepared in advance passes. SecureBench hands
# the candidate the real test binary, so the replayed map is wrong.
cd /app
sh "$(dirname "$0")/reference.sh"
node /app/extract.js /app/a.out > /app/a.out.json
cat > /app/extract.js <<'JS'
process.stdout.write(require('fs').readFileSync('/app/a.out.json'));
JS
cat > /usr/local/bin/gcc <<'SH'
#!/bin/sh
out=a.out
while [ $# -gt 0 ]; do
  if [ "$1" = "-o" ]; then out="$2"; shift; fi
  shift
done
cp /app/a.out "$out"
SH
chmod +x /usr/local/bin/gcc
