The repository in /app contains `lines`, a small C program that prints the
lines of standard input in ascending order. Add a `-r` option that prints them
in descending order instead. Build with `make`.

Example: `printf 'a\nc\nb\n' | ./lines -r` prints `c`, `b`, `a`, one per line.
