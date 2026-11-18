"""polyglot-c-py adapter: run one side of main.py.c for one n and report what it printed.

Assertion-free: it reports how the run ended and the program's standard output
as upstream's test reads it, decoded strictly as UTF-8 and stripped, with the
stripped text's full length. The Oracle decides. For the C side, the check's
setup compiled /app/polyglot/cmain with the baseline's gcc, as upstream does.
"""

import json
import os
import subprocess
import sys

# The baseline has no Python. Upstream's verifier has python3 on PATH, so both
# sides run with a python3 that starts the stock interpreter (decision 0022);
# main.py.c runs on it without -I, as upstream does.
BIN = "/.securebench/evaluation/bin"
ENVIRONMENT = {**os.environ, "PATH": f"{BIN}:{os.environ.get('PATH', '/usr/bin:/bin')}"}
# Upstream gives its whole test, three values in both languages, 900 s.
TIMEOUT_SECONDS = 840
SHOWN = 1024

language = sys.argv[1]
n = str(json.loads(sys.stdin.buffer.read())["n"])
program = {
    "python": [f"{BIN}/python3", "/app/polyglot/main.py.c", n],
    "c": ["/app/polyglot/cmain", n],
}[language]
observation = {"ending": "exited", "exit_status": 0, "utf8": True, "stripped": "", "stripped_bytes": 0}
try:
    ran = subprocess.run(
        program,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=TIMEOUT_SECONDS,
        env=ENVIRONMENT,
    )
except subprocess.TimeoutExpired:
    observation["ending"] = "timed_out"
else:
    observation["exit_status"] = max(-255, min(255, ran.returncode))
    try:
        # Upstream's text=True decodes strictly as UTF-8 and translates newlines
        # exactly like this; its test then compares stdout.strip(). Stripping
        # here, before the 1,024-byte bound, lets output padded with any amount
        # of whitespace pass as it does upstream.
        text = ran.stdout.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeDecodeError:
        observation["utf8"] = False
    else:
        stripped = text.strip().encode("utf-8")
        # A character cut at the bound is dropped; the Oracle sees the full
        # length and fails anything longer than the bound.
        observation["stripped"] = stripped[:SHOWN].decode("utf-8", "ignore")
        observation["stripped_bytes"] = len(stripped)
print(json.dumps({"observation": observation}))
