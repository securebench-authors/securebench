"""Run the binary setup.sh built for one language on one input and report what it printed.

Upstream's test runs each binary with subprocess.run(check=True, text=True)
and compares stdout.strip() with the expected number. We report the exit
status and the stripped text, decoded the same way (strict UTF-8), and leave
every comparison to the Oracle.
"""

import json
import subprocess
import sys

BINARIES = {"rust": "/app/polyglot/main", "cpp": "/app/polyglot/cmain"}

# Only the stripped text is compared upstream, so we strip here: a correct
# program may print any amount of surrounding whitespace, and only the
# stripped text has to fit the observation.
MAX_STRIPPED_BYTES = 65536


def run(binary: str, n: int) -> dict[str, object]:
    try:
        completed = subprocess.run(
            [binary, str(n)],
            cwd="/app",
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError as error:
        return {"launch_error": type(error).__name__}
    result: dict[str, object] = {
        "exit_status": completed.returncode,
        "stdout_bytes": len(completed.stdout),
    }
    try:
        # text=True upstream also turns \r\n and \r into \n; that never
        # changes what strip() leaves at the ends, and the expected values
        # contain no line breaks.
        text = completed.stdout.decode("utf-8")
    except UnicodeDecodeError:
        result["stdout_error"] = "stdout is not valid UTF-8"
        return result
    stripped = text.strip()
    if len(stripped.encode("utf-8")) > MAX_STRIPPED_BYTES:
        result["stdout_error"] = "stripped stdout is over 64 KiB"
        return result
    result["stdout_stripped"] = stripped
    return result


def main() -> None:
    binary = BINARIES[sys.argv[1]]
    challenge = json.load(sys.stdin)
    sys.stdout.write(json.dumps({"observation": run(binary, challenge["n"])}))


main()
