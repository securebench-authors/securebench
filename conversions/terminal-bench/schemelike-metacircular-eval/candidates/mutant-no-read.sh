#!/bin/sh
# The reference without the read primitive, so the interpreted program gets
# none of the remaining input.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i "/(define-var! 'read /d" eval.scm
! grep -q "(define-var! 'read " eval.scm
