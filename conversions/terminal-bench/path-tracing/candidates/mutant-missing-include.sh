#!/bin/sh
# The reference with `#include<stdlib.h>` dropped to save bytes. gcc 13 still
# builds it, warning about the implicit declarations of malloc and free, and the
# image is exact. The warnings name /app/image.c, so `gcc -H` mentions /app/ and
# upstream's test_no_deps fails.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i '/^#include<stdlib.h>$/d' image.c
grep -q 'stdlib' image.c && { rm -f image.c; exit 1; }
exit 0
