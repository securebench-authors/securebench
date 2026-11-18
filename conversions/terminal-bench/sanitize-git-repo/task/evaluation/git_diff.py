"""Report what Git says changed in the replayed repository since a commit.

This repeats test_no_other_files_changed's Git calls: GitPython 3.1.44's
`repo.commit(<commit>)` and `commit.diff(None)`, which run
`git diff <commit> --abbrev=40 --full-index -M --raw -z --no-color` with
LANGUAGE=C and LC_ALL=C and parse the raw records. The adapter returns every
record's paths; the Oracle decides which paths may change.
"""

import json
import os
import subprocess
import sys

GIT = "/usr/bin/git"


def run(repository: str, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    environment = dict(os.environ)
    environment["LANGUAGE"] = "C"
    environment["LC_ALL"] = "C"
    # GitPython's Repo(path) opens only `path`; Git must not climb to a parent.
    environment["GIT_CEILING_DIRECTORIES"] = os.path.dirname(repository)
    return subprocess.run(
        [GIT, *arguments],
        cwd=repository,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
    )


def parse_raw(output: bytes) -> list[dict[str, str]]:
    # GitPython's Diff._handle_diff_line, keeping only what the test reads.
    text = output.decode("utf-8")
    _, _, text = text.partition(":")
    entries = []
    for record in text.split("\x00:"):
        if not record:
            continue
        meta, _, path = record.partition("\x00")
        path = path.rstrip("\x00").strip("\n")
        status = meta.split(None, 4)[4]
        a_path = b_path = path
        if status[0] in ("C", "R"):
            a_path, b_path = path.split("\x00", 1)
        entries.append({"status": status, "a_path": a_path, "b_path": b_path})
    return entries


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    repository = challenge["repository"]
    commit = challenge["commit"]
    found = run(repository, "cat-file", "-t", commit)
    diff = run(
        repository,
        "diff",
        commit,
        "--abbrev=40",
        "--full-index",
        "-M",
        "--raw",
        "-z",
        "--no-color",
    )
    try:
        entries = parse_raw(diff.stdout)
    except (UnicodeDecodeError, IndexError, ValueError) as error:
        # GitPython raises on the same records, so the native test errors too.
        print(json.dumps({"unable": {"code": "unparsable-diff", "message": str(error)[:4000]}}))
        return
    observation = {
        "commit_found": found.returncode == 0 and found.stdout.strip() == b"commit",
        "diff_exit_status": diff.returncode,
        "entries": entries,
    }
    print(json.dumps({"observation": observation}))


main()
