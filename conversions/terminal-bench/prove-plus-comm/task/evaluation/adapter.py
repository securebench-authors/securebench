"""Compile the candidate's proof with the baseline's coqc and report what happened.

This is upstream's test_compiled_proof_content: `coqc plus_comm.v` in the
working directory, judged on its exit status. coqc is /usr/bin/coqc from the
baseline image, outside the scope, so the candidate cannot replace it.
"""

import json
import subprocess
import sys

COQC = "/usr/bin/coqc"
WORKDIR = "/workspace"
# The baseline image's own environment; the stock interpreter's loader
# arguments are not passed on to coqc.
ENVIRONMENT = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
}
TAIL_LINES = 64
LINE_BYTES = 1024


def _strict_utf8(data: bytes) -> bool:
    # Upstream runs coqc with subprocess.run(text=True), which decodes both
    # streams strictly as UTF-8 and raises, failing the test, when it cannot.
    try:
        data.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return False
    return True


def _tail(stdout: bytes, stderr: bytes) -> list[str]:
    # For diagnostics only: the Oracle does not judge coqc's messages.
    lines = []
    for stream in (stdout, stderr):
        lines.extend(stream.decode("utf-8", "replace").splitlines())
    result = []
    for line in lines[-TAIL_LINES:]:
        result.append(line.encode("utf-8")[:LINE_BYTES].decode("utf-8", "ignore"))
    return result


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    try:
        completed = subprocess.run(
            [COQC, challenge["source"]],
            cwd=WORKDIR,
            env=ENVIRONMENT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        response = {"unable": {"code": "coqc-not-started", "message": str(error)[:1024]}}
    else:
        response = {
            "observation": {
                "exit_status": completed.returncode,
                "output_utf8": _strict_utf8(completed.stdout) and _strict_utf8(completed.stderr),
                "output_tail": _tail(completed.stdout, completed.stderr),
            }
        }
    sys.stdout.write(json.dumps(response, ensure_ascii=True))


main()
