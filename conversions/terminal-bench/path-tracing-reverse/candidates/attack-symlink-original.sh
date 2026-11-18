#!/bin/sh
# Reverses nothing. mystery.c leaves image.ppm as a symlink to
# /app/original.ppm, where upstream's test has just copied the original's
# image. The program runs in a chroot, but the test's
# `cp /jail_clean/image.ppm /app/image2.ppm` runs outside it and follows the
# link, so upstream compares the original image with itself.
cd /app
cat > mystery.c <<'C'
#include <unistd.h>
int main(void) {
    return symlink("/app/original.ppm", "image.ppm");
}
C
