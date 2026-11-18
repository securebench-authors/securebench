"""Apply the candidate's /app/re.json to each FEN in the challenge.

This is upstream's run_solution up to the point where it has the final string:
the same json.load of /app/re.json and the same re.sub loop, on the baseline's
Python 3.13 (the version upstream's test.sh asks uv for). The adapter returns
each final string unchanged; splitting it into positions, dropping the move
counters and comparing with python-chess are the Oracle's job.

It runs with -I, so neither /app (the working directory) nor any other
candidate path is on sys.path, and the json and re modules come from the
baseline's standard library, which lies outside the scope.
"""

import json
import re
import sys


def run_regexes(fen):
    for pattern, repl in json.load(open("/app/re.json")):
        fen = re.sub(pattern, repl, fen)
    return fen


def main():
    challenge = json.load(sys.stdin)
    outputs = []
    for fen in challenge["fens"]:
        try:
            outputs.append(run_regexes(fen))
        except Exception as error:  # noqa: BLE001 - upstream's test errors on any exception
            message = f"{type(error).__name__}: {error}".encode(errors="replace")[:4096].decode(errors="ignore")
            json.dump({"unable": {"code": "regexes-raised", "message": message}}, sys.stdout)
            return
    json.dump({"observation": {"outputs": outputs}}, sys.stdout)


main()
