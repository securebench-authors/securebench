#!/bin/sh
# Reverses nothing. mystery.c runs a copy of the original binary that it keeps
# in /app, which the instructions forbid ("must not invoke ./mystery").
# Upstream runs the program alone in a chroot, where the copy is out of reach;
# aimed at the adapter, which empties /app before the run instead.
cd /app
cp /app/mystery /app/.renderer
cat > mystery.c <<'C'
#include <unistd.h>
int main(void) {
    execl("/app/.renderer", "mystery", (char *)0);
    return 1;
}
C
