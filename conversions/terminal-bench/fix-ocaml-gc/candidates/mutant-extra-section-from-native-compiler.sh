#!/bin/sh
# The upstream fix, plus a native-code ocamlc (ocamlc.opt) that adds an empty
# section named XTRA to every bytecode executable. tools/cmpbyt compares every
# section except DBUG, so the native grader's compare-bytecode-programs fails;
# it checks that the conversion's reimplementation of cmpbyt
# (oracle.same_bytecode) is not more lenient.
HERE=$(cd "$(dirname "$0")" && pwd) || exit 1
cd /app || exit 1
sh "$HERE/reference.sh" || exit 1
cd /app/ocaml/bytecomp || exit 1
sed -n '527p' bytelink.ml | grep -q '^       Bytesections.record toc_writer CRCS;$' || exit 1
sed -i '527s/Bytesections.record toc_writer CRCS;/Bytesections.record toc_writer CRCS;\n       if Sys.backend_type = Sys.Native then\n         Bytesections.record toc_writer (Bytesections.Name.of_string "XTRA");/' bytelink.ml
