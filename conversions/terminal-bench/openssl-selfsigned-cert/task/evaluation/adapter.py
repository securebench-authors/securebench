"""openssl-selfsigned-cert adapter: run what upstream's tests run and report what it printed.

Assertion-free. For each command it reports how the run ended, its exit
status, the first bytes of standard output decoded as UTF-8, the full output
length, and whether standard output and standard error were valid UTF-8
(upstream decodes both strictly, so invalid bytes fail its test). The Oracle
decides.

`openssl` runs upstream's four openssl commands with the baseline's openssl,
and reports whether the key, following links as upstream's `os.stat` does,
has the owner execute bit; no candidate code runs. `check-script` runs
`python /app/check_cert.py` with the baseline's Python on the delivered
files, as upstream does.

Replay writes every file without the execute bit as mode 0644, so before the
script runs the key is set to 0600, the mode the instructions require and the
agent set: a correct script may check it, as upstream's run would let it.
"""

import json
import os
import stat
import subprocess
import sys

KEY = "/app/ssl/server.key"
CERTIFICATE = "/app/ssl/server.crt"
PEM = "/app/ssl/server.pem"
SCRIPT = "/app/check_cert.py"
# The image's PATH, used when the environment gives none: the script runs
# `python` from /usr/local/bin, and may run `openssl` from /usr/bin.
IMAGE_PATH = "/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"


def run(command: list[str], timeout: int, shown: int) -> dict[str, object]:
    environment = dict(os.environ)
    environment.setdefault("PATH", IMAGE_PATH)
    try:
        ran = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            env=environment,
            cwd="/app",
        )
    except subprocess.TimeoutExpired:
        return {
            "ending": "timed_out",
            "exit_status": 0,
            "stdout": "",
            "stdout_bytes": 0,
            "stdout_utf8": True,
            "stderr_utf8": True,
        }
    return {
        "ending": "exited",
        "exit_status": max(-255, min(255, ran.returncode)),
        # Whatever "ignore" drops, the Oracle sees through stdout_utf8 and stdout_bytes.
        "stdout": ran.stdout[:shown].decode("utf-8", "ignore"),
        "stdout_bytes": len(ran.stdout),
        "stdout_utf8": utf8(ran.stdout),
        "stderr_utf8": utf8(ran.stderr),
    }


def utf8(data: bytes) -> bool:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def key_mode() -> str:
    try:
        info = os.stat(KEY)
    except OSError:
        return "not_a_file"
    if not stat.S_ISREG(info.st_mode):
        return "not_a_file"
    return "owner_execute" if info.st_mode & stat.S_IXUSR else "no_owner_execute"


def openssl() -> dict[str, object]:
    # Each run gets 200 s, so all four fit the case's 900 s.
    shown = 131072
    return {
        "key_mode": key_mode(),
        "key_text": run(["openssl", "rsa", "-in", KEY, "-text", "-noout"], 200, shown),
        "certificate_text": run(
            ["openssl", "x509", "-in", CERTIFICATE, "-text", "-noout"], 200, shown
        ),
        "certificate_dates": run(
            ["openssl", "x509", "-in", CERTIFICATE, "-noout", "-dates"], 200, shown
        ),
        "pem_certificate": run(["openssl", "x509", "-in", PEM, "-text", "-noout"], 200, shown),
    }


def check_script() -> dict[str, object]:
    if os.path.isfile(KEY):
        os.chmod(KEY, 0o600)
    return run(["python", SCRIPT], 840, 65536)


def main() -> None:
    # The challenge is empty: both checks run upstream's fixed commands.
    json.loads(sys.stdin.buffer.read())
    if sys.argv[1] == "openssl":
        observation = openssl()
    else:
        try:
            observation = check_script()
        except OSError as error:
            unable = {"code": "prepare-failed", "message": str(error)[:1024]}
            sys.stdout.buffer.write(json.dumps({"unable": unable}).encode("utf-8"))
            return
    response = json.dumps({"observation": observation}, ensure_ascii=False)
    sys.stdout.buffer.write(response.encode("utf-8"))


main()
