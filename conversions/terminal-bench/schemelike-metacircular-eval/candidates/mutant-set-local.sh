#!/bin/sh
# The reference with set! defining the variable in the innermost frame instead
# of updating the binding where it lives, so closures never see their own
# updates (a counter returns 1 every time).
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i 's/(set-var! (cadr exp)/(define-var! (cadr exp)/' eval.scm
! grep -q '(set-var! (cadr exp)' eval.scm
