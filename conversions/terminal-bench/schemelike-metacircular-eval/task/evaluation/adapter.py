"""schemelike-metacircular-eval adapter: run one program through /app/eval.scm and report its output.

Assertion-free. It lays out a run directory as upstream's test does (interp.py,
eval.scm and the program side by side), runs

    python3 interp.py /app/eval.scm

there with the program's name and input on standard input, and reports how the
run ended and what it printed. The Oracle decides.

Mode "once" interprets the program with eval.scm. Mode "twice" gives eval.scm
the line "/app/eval.scm" first, as upstream's metacirc run does, so that
eval.scm interprets itself, which interprets the program.

The output is decoded as upstream's `subprocess.run(..., text=True)` decodes
it: strict UTF-8 with "\\r\\n" and "\\r" read as "\\n". Leading and trailing
whitespace is removed, as the first step of upstream's normalize_output does,
so that whitespace upstream ignores never pushes an output past the bound.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EVALUATION = Path("/.securebench/evaluation")
EVAL_SCM = Path("/app/eval.scm")
# The baseline's own Python 3.13, outside the scope, which is the version
# upstream's verifier runs interp.py on.
PYTHON = "/usr/local/bin/python3"
# Upstream's timeout for each run through eval.scm.
TIMEOUT_SECONDS = 60
SHOWN = 16384


def file_name(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.endswith(".scm")
        or "/" in value
        or "\n" in value
        or value in (".", "..")
    ):
        raise SystemExit(f"bad file name {value!r}")
    return value


def main() -> None:
    mode = sys.argv[1]
    challenge = json.loads(sys.stdin.buffer.read())
    name = file_name(challenge["name"])
    lines = f"{name}\n{challenge['input']}"
    run = Path(tempfile.mkdtemp(prefix="run-"))
    shutil.copyfile(EVALUATION / "interp.py", run / "interp.py")
    if EVAL_SCM.is_file():
        shutil.copyfile(EVAL_SCM, run / "eval.scm")
    (run / name).write_text(challenge["program"], encoding="utf-8")
    if mode == "twice":
        lines = f"{EVAL_SCM}\n{lines}"
    elif mode != "once":
        raise SystemExit(f"unknown mode {mode!r}")
    try:
        ran = subprocess.run(
            # -I keeps the run directory off sys.path, so no file a run writes
            # there can be imported by a later Python start.
            [PYTHON, "-I", "interp.py", str(EVAL_SCM)],
            cwd=run,
            input=lines.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        observation = {"ending": "timed_out", "utf8": True, "text": "", "text_bytes": 0}
    else:
        try:
            text = ran.stdout.decode("utf-8")
        except UnicodeDecodeError:
            observation = {"ending": "exited", "utf8": False, "text": "", "text_bytes": 0}
        else:
            text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
            encoded = text.encode("utf-8")
            observation = {
                "ending": "exited",
                "utf8": True,
                # A cut inside a character drops its bytes; the Oracle sees the
                # cut through text_bytes.
                "text": encoded[:SHOWN].decode("utf-8", "ignore"),
                "text_bytes": len(encoded),
            }
    print(json.dumps({"observation": observation}))


main()
