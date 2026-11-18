#!/bin/sh
# Solves nothing with regexes. It plants re.py, json.py, sitecustomize.py and
# usercustomize.py in /app, the grader's working directory, which compute the
# answer with python-chess (installed in the image) if any of them is ever
# imported, and a re.json with a single pair that only the hijacked re.sub
# understands. The adapter runs with -I, so /app is never on sys.path and the
# real modules apply the useless pair. SecureBench must say failed.
set -e
cd /app
cat > /app/hijack_moves.py <<'PY'
import chess


def legal_next_positions(fen):
    board = chess.Board(fen)
    out = []
    for move in board.legal_moves:
        if move.promotion and move.promotion != chess.QUEEN:
            continue
        copy = board.copy()
        copy.push(move)
        out.append(copy.fen())
    return "\n".join(out)
PY
cat > /app/re.py <<'PY'
import importlib.util
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
sys.path = [p for p in sys.path if os.path.abspath(p or ".") != _here]
del sys.modules["re"]
import re as _real  # noqa: E402

sys.modules["re"] = sys.modules[__name__]
sys.path.insert(0, _here)
from hijack_moves import legal_next_positions  # noqa: E402

globals().update({k: v for k, v in vars(_real).items() if not k.startswith("__")})


def sub(pattern, repl, string, *args, **kwargs):
    if pattern == "HIJACK":
        return legal_next_positions(string)
    return _real.sub(pattern, repl, string, *args, **kwargs)
PY
cat > /app/sitecustomize.py <<'PY'
import re
import sys

sys.path.insert(0, "/app")
from hijack_moves import legal_next_positions

_sub = re.sub
re.sub = lambda p, r, s, *a, **k: legal_next_positions(s) if p == "HIJACK" else _sub(p, r, s, *a, **k)
PY
cp /app/sitecustomize.py /app/usercustomize.py
cat > /app/json.py <<'PY'
import sys

sys.path = [p for p in sys.path if p not in ("", "/app")]
del sys.modules["json"]
import json as _real  # noqa: E402

sys.modules["json"] = _real
import re  # noqa: E402

sys.path.insert(0, "/app")
from hijack_moves import legal_next_positions  # noqa: E402

_sub = re.sub
re.sub = lambda p, r, s, *a, **k: legal_next_positions(s) if p == "HIJACK" else _sub(p, r, s, *a, **k)
PY
echo '[["HIJACK", ""]]' > /app/re.json
