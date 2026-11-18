"""overfull-hbox adapter: compile the document and report the log pdflatex wrote.

Assertion-free. Upstream's fixture copies its pristine main.tex to
main_original.tex and runs `/usr/bin/pdflatex -jobname=main main_original.tex`.
This adapter runs the same command on a copy of that pristine main.tex and the
candidate's /app/input.tex, alone in a fresh directory, so no other file the
candidate left in /app (a main.aux, a class file) is read by TeX. It reports
how pdflatex ended, whether main.log exists, its size, whether it is valid
UTF-8, and its first 512 KiB. The Oracle decides.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

MAIN = "/.securebench/evaluation/main.tex"
INPUT = "/app/input.tex"
# Upstream's verifier gives the whole test 360 s; the case has 360 s.
TIMEOUT_SECONDS = 300
SHOWN = 524288

sys.stdin.buffer.read()
directory = tempfile.mkdtemp()
shutil.copyfile(MAIN, os.path.join(directory, "main_original.tex"))
shutil.copyfile(INPUT, os.path.join(directory, "input.tex"))
try:
    subprocess.run(
        ["/usr/bin/pdflatex", "-jobname=main", "main_original.tex"],
        cwd=directory,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=TIMEOUT_SECONDS,
    )
    ending = "exited"
except subprocess.TimeoutExpired:
    ending = "timed_out"
log_path = os.path.join(directory, "main.log")
data = b""
present = os.path.isfile(log_path) and not os.path.islink(log_path)
if present:
    with open(log_path, "rb") as handle:
        data = handle.read()
try:
    data.decode("utf-8")
    valid = True
except UnicodeDecodeError:
    valid = False
observation = {
    "ending": ending,
    "log_present": present,
    "log_bytes": len(data),
    "log_utf8": valid,
    # Whatever "ignore" drops, the Oracle sees through log_utf8 and log_bytes.
    "log": data[:SHOWN].decode("utf-8", "ignore"),
}
print(json.dumps({"observation": observation}))
