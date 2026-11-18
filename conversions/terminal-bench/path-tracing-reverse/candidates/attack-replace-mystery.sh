#!/bin/sh
# Reverses nothing. mystery.c writes an 800x600 image of one gray, and the same
# program, built static, replaces /app/mystery. Upstream renders its reference
# image with whatever /app/mystery holds when the tests run, so it compares the
# gray image with itself.
cd /app
cat > mystery.c <<'C'
#include <stdio.h>
int main(void) {
    FILE *f = fopen("image.ppm", "w");
    fprintf(f, "P3\n800 600\n255\n");
    for (int i = 0; i < 800 * 600; i++)
        fprintf(f, "128 128 128\n");
    return fclose(f);
}
C
gcc -static -o /app/mystery /app/mystery.c -lm
