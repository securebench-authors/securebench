#!/bin/sh
# The upstream fix, plus a bytecode runtime that writes CRLF line endings on
# standard output and standard error. ocamltest's text comparison accepts
# output whose lines all end in CRLF against an LF reference, so the native
# grader should pass this; it aims at the conversion's reimplementation of that
# comparison (oracle.same_text). The replacement function head is in
# crlf-write-fd.c; it takes the place of the first three lines of
# caml_write_fd in runtime/unix.c.
HERE=$(cd "$(dirname "$0")" && pwd) || exit 1
cd /app || exit 1
sh "$HERE/reference.sh" || exit 1
cd /app/ocaml/runtime || exit 1
grep -q '^int caml_write_fd(int fd, int flags, void \* buf, int n)$' unix.c || exit 1
awk -v patch="$HERE/crlf-write-fd.c" '
  /^int caml_write_fd\(int fd, int flags, void \* buf, int n\)$/ {
    while ((getline line < patch) > 0) print line
    skip = 2
    next
  }
  skip > 0 { skip--; next }
  { print }' unix.c > unix.c.new && mv unix.c.new unix.c
grep -q 'write(fd, "\\r\\n", 2)' unix.c || exit 1
