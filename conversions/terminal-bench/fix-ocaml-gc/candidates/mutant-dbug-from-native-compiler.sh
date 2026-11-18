#!/bin/sh
# The upstream fix, plus a native-code ocamlc (ocamlc.opt) that always writes a
# (possibly empty) DBUG section. tools/cmpbyt ignores DBUG sections, so the
# native grader's compare-bytecode-programs still passes; it aims at the
# conversion's reimplementation of cmpbyt (oracle.same_bytecode).
HERE=$(cd "$(dirname "$0")" && pwd) || exit 1
cd /app || exit 1
sh "$HERE/reference.sh" || exit 1
cd /app/ocaml/bytecomp || exit 1
sed -n '529p' bytelink.ml | grep -q '^       if !Clflags.debug then begin$' || exit 1
sed -i '529s/if !Clflags.debug then begin/if !Clflags.debug || Sys.backend_type = Sys.Native then begin/' bytelink.ml
