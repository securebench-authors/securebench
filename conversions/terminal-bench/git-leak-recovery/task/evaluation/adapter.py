"""Run upstream's git commands on the replayed repository and report what they printed.

The challenge lists git argument vectors from upstream's tests. Each runs as
`git -C /app/repo <args>`, as upstream's `subprocess.run` calls do. With
`inspect_dangling`, every line of the last command's output that mentions
"dangling" is followed by `git cat-file -p <last word>`, as
test_no_secrets_in_unreachable_objects does. The adapter decides nothing: the
Oracle reads the outputs.
"""

import json
import subprocess
import sys

GIT = "/usr/bin/git"
REPO = "/app/repo"
# The environment upstream's verifier gives git: root's home and the image's
# PATH. Harbor sets no locale, so Python 3.13 coerces the C locale (PEP 538) and
# exports LC_CTYPE=C.UTF-8 to its children; git's case-insensitive --grep then
# folds case with Unicode rules.
ENV = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LC_CTYPE": "C.UTF-8",
}


def run(args: list[str]) -> dict[str, object]:
    done = subprocess.run([GIT, "-C", REPO, *args], capture_output=True, env=ENV, check=False)
    # Upstream decodes both streams with text=True: strict UTF-8, then universal
    # newlines. A decoding error raises there, so it is reported rather than
    # repaired. Standard error is otherwise unused, so only whether it decodes
    # is reported.
    try:
        done.stderr.decode("utf-8", "strict")
        stderr_decoded = True
    except UnicodeDecodeError:
        stderr_decoded = False
    try:
        text = done.stdout.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return {
            "returncode": done.returncode,
            "decoded": False,
            "stderr_decoded": stderr_decoded,
            "stdout": "",
        }
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return {
        "returncode": done.returncode,
        "decoded": True,
        "stderr_decoded": stderr_decoded,
        "stdout": text,
    }


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    commands = [run(args) for args in challenge["commands"]]
    dangling: list[dict[str, object]] = []
    if challenge["inspect_dangling"] and commands[-1]["decoded"]:
        for line in str(commands[-1]["stdout"]).splitlines():
            if "dangling" in line:
                obj = line.split()[-1]
                dangling.append({"object": obj, **run(["cat-file", "-p", obj])})
    sys.stdout.write(json.dumps({"observation": {"commands": commands, "dangling": dangling}}))


if __name__ == "__main__":
    main()
