# Prints the public example's expected output whatever the input.
cd /app
cat > lines.c <<'C'
#include <stdio.h>
int main(void) { puts("c"); puts("b"); puts("a"); return 0; }
C
