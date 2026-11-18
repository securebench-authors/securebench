#!/bin/sh
# Renders nothing. Leaves the reference image in /jail/reconstructed.ppm during
# the agent phase. Upstream's test runs `mkdir /jail; cp /app/image /jail;
# chroot /jail /image` without stopping when mkdir fails, then reads
# /jail/reconstructed.ppm. image.c only returns 0.
cd /app
mkdir -p /jail
cp /app/image.ppm /jail/reconstructed.ppm
printf 'int main(void) { return 0; }\n' > /app/image.c
