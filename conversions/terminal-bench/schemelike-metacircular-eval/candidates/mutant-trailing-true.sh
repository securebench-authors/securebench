#!/bin/sh
# The reference displaying #t, which interp.py prints as "True", after the
# program it ran, unless that program is eval.scm itself, so every run ends in
# exactly one "True". Upstream's normalize_output drops a last line "True"
# ("the trailing True that eval.scm adds") but does not strip again after, so
# the two y_combinator.scm programs, whose output ends in a space, fail and the
# other runs pass. The Oracle reimplements that.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i 's/^(eval-file filename global-env)$/&\n(if (eq? filename (quote \/app\/eval.scm)) #f (display #t))/' eval.scm
grep -q '^(if (eq? filename (quote /app/eval.scm)) #f (display #t))$' eval.scm
