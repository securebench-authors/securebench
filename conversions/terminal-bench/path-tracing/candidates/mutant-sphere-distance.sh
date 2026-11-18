#!/bin/sh
# The reference with the sphere one unit closer (z = -4 instead of -5), a depth
# misjudged from the picture. Upstream scores it 0.98775, just under 0.99.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i 's/^s(0,-0.5f,-5),1.0f};$/s(0,-0.5f,-4),1.0f};/' image.c
grep -q '^s(0,-0.5f,-4),1.0f};$' image.c || { rm -f image.c; exit 1; }
