#!/bin/sh
# The reference with a newline primitive that prints a carriage return instead
# of a line feed. Upstream reads the output with text=True, which turns "\r"
# into "\n"; the adapter reimplements that decoding, and this mutant runs
# through it on every line.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i "s/^  (define-var! 'newline (make-primitive (lambda (args) (newline) #f)) initial-env)$/  (define-var! 'newline (make-primitive (lambda (args) (putchr 13) #f)) initial-env)/" eval.scm
grep -q "(define-var! 'newline (make-primitive (lambda (args) (putchr 13) #f)) initial-env)" eval.scm
