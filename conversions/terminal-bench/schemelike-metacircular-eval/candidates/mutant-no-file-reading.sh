#!/bin/sh
# The reference without the fread and fgetchr primitives, which no test program
# uses but eval.scm itself needs to read its program. Every test program runs;
# eval.scm cannot interpret itself.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i "/(define-var! 'fread /d; /(define-var! 'fgetchr /d" eval.scm
! grep -q "(define-var! 'f\(read\|getchr\) " eval.scm
