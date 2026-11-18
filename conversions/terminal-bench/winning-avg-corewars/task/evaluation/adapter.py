"""Run upstream's pmars battle for one opponent and report what pmars printed.

Upstream's test runs `pmars -b -r 100 -f /app/my_warrior.red /app/warriors/<opponent>`
with `subprocess.run(..., capture_output=True, text=True)`. We run the same command
with the baseline's pmars, which lies outside the scope, so the candidate cannot replace
it. The opponent comes from our own copy in `evaluation/`: the `opponents` artifact
check has already required `/app/warriors` to match upstream's hashes byte for byte,
so the two copies are identical whenever this case runs.

We report the exit status and the standard output lines; the Oracle parses the win count
exactly as upstream's test does.
"""

import json
import subprocess
import sys

PMARS = "/usr/local/bin/pmars"
WARRIOR = "/app/my_warrior.red"
OPPONENTS = "/.securebench/evaluation/warriors/"
KNOWN = ("stone.red", "vampire.red", "paper.red", "snake.red", "g2-clear.red")


def emit(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def main():
    challenge = json.loads(sys.stdin.read())
    opponent = challenge["opponent"]
    if opponent not in KNOWN:
        emit({"unable": {"code": "unknown-opponent", "message": opponent[:200]}})
        return
    result = subprocess.run(
        [PMARS, "-b", "-r", "100", "-f", WARRIOR, OPPONENTS + opponent],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    try:
        text = result.stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        # Upstream's text=True capture raises here, which fails its test; the
        # observation schema holds only text, so this is our failure channel.
        emit({"unable": {"code": "stdout-not-utf8", "message": str(error)[:1000]}})
        return
    # The same newline translation subprocess applies with text=True.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    emit({"observation": {"exit_code": result.returncode, "stdout_lines": text.split("\n")}})


main()
