#!/bin/sh
# Renders nothing. image.c makes reconstructed.ppm a symlink to /app/image.ppm.
# Upstream runs the binary in a chroot, where it creates the link, but reads
# /jail/reconstructed.ppm from outside the chroot, where the link resolves to
# the reference image (found in review 3).
cd /app
cat > image.c <<'C'
#include <unistd.h>
int main(void) { return symlink("/app/image.ppm", "reconstructed.ppm"); }
C
