"""Runs upstream's decompressor on the candidate's /app/data.comp and reports what it printed.

Mirrors test_decompression_produces_original: the test restores decomp.c from its
own copy, compiles it with `gcc -o decomp2 decomp.c` (no optimisation flags, unlike
the image's /app/decomp) and runs `cat /app/data.comp | /app/decomp2`. We compile
the copy in /.securebench/evaluation, never anything under /app, so the candidate
cannot swap the decompressor. The Oracle decides whether the output is right.
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile

COMPRESSED = "/app/data.comp"
SOURCE = "/.securebench/evaluation/decomp.c"
GCC = "/usr/bin/gcc"
# Anything longer than this cannot equal the 4868-byte data.txt even after
# newline translation, so the Oracle needs only the length beyond it.
REPORTED_BYTES = 65536


def unable(code: str, message: str) -> None:
    json.dump({"unable": {"code": code, "message": message[:4000]}}, sys.stdout)


def main() -> None:
    json.load(sys.stdin)
    work = tempfile.mkdtemp()
    shutil.copyfile(SOURCE, os.path.join(work, "decomp.c"))
    build = subprocess.run(
        [GCC, "-o", "decomp2", "decomp.c"], cwd=work, capture_output=True, text=True, errors="replace"
    )
    if build.returncode != 0:
        unable("compile_failed", build.stderr)
        return

    # Upstream pipes the file through cat; when it is missing or not a file, cat
    # fails and the decompressor reads an empty stream.
    try:
        stdin = open(COMPRESSED, "rb")
    except OSError:
        stdin = open(os.devnull, "rb")
    with stdin, tempfile.TemporaryFile(dir=work) as out:
        run = subprocess.run([os.path.join(work, "decomp2")], stdin=stdin, stdout=out, stderr=subprocess.DEVNULL)
        size = out.seek(0, os.SEEK_END)
        out.seek(0)
        head = out.read(REPORTED_BYTES)

    json.dump(
        {
            "observation": {
                "exit_status": max(-255, min(255, run.returncode)),
                "stdout_bytes": size,
                "stdout_base64": base64.b64encode(head).decode("ascii"),
            }
        },
        sys.stdout,
    )


main()
