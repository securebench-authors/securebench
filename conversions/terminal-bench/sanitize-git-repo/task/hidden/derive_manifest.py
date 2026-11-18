"""Derive hidden/manifest.json from the baseline image.

Run inside the unmodified baseline, where the working tree is clean:

    docker run --rm -v <this dir>:/derive:ro <baseline image> \
        python3 -B /derive/derive_manifest.py > manifest.json

The manifest lists every path of the upstream test's reference commit tree,
except the three files the task asks to change, with the SHA-256 and the
executable bit of the file the baseline holds at that path. It is the trusted
form of "no other file changed": the Oracle compares it with the candidate's
listing, which SecureBench computes on the host.
"""

import hashlib
import json
import os
import subprocess
import sys

REPOSITORY = "/app/dclm"
# The commit test_no_other_files_changed diffs the working tree against.
COMMIT = "d6987af002b122fef54bc0be402062c76488a4d9"
CONTAMINATED = [
    "ray_processing/ray_cluster.yaml",
    "ray_processing/process.py",
    "exp_data/datasets/tokenized/rw_v2_fasttext_openhermes_vs_rw_v2_bigram_0.1_arcade100k.json",
]


def git(*arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", REPOSITORY, *arguments], check=True, capture_output=True
    ).stdout


def main() -> None:
    # The working tree must hold the commit's content everywhere but the
    # contaminated files, or the baseline file would not be the reference.
    changed = git("diff", "--name-only", "-z", COMMIT).decode().split("\0")
    unexpected = [path for path in changed if path and path not in CONTAMINATED]
    if unexpected or git("status", "--porcelain", "--ignored"):
        sys.exit(f"baseline differs from {COMMIT}: {unexpected}")
    files = {}
    for record in git("ls-tree", "-r", "-z", COMMIT).decode().split("\0"):
        if not record:
            continue
        meta, path = record.split("\t", 1)
        mode = meta.split(" ")[0]
        if mode not in ("100644", "100755"):
            sys.exit(f"unexpected mode {mode} for {path}")
        if path in CONTAMINATED:
            continue
        full = os.path.join(REPOSITORY, path)
        with open(full, "rb") as file:
            digest = "sha256:" + hashlib.sha256(file.read()).hexdigest()
        files[path] = {"sha256": digest, "executable": mode == "100755"}
    json.dump({"commit": COMMIT, "files": files}, sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")


main()
