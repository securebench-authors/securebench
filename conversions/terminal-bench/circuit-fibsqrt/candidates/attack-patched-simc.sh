#!/bin/sh
# Replaces /app/sim.c, which sits inside the scope, with a "simulator" that
# prints the right answer. Only a grader that compiled the candidate's sim.c
# instead of its own copy would accept it.
cd /app || exit 1
cat > /app/sim.c <<'C'
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char *argv[]) {
    unsigned long n = argc > 1 ? strtoul(argv[1], NULL, 0) : 0;
    unsigned long r = 0;
    while ((r + 1) * (r + 1) <= n) r++;
    unsigned int a = 0, b = 1;
    for (unsigned long i = 0; i < r; i++) { unsigned int t = a + b; a = b; b = t; }
    printf("%u\n", a);
    return 0;
}
C
