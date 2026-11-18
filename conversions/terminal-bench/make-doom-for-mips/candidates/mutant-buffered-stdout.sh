#!/bin/sh
# The reference with stdout fully buffered: writes to file descriptors 0 and 1
# collect in a 64 KiB buffer that is written out only when it is full. DOOM
# prints about 2 KB at start-up and nothing per frame, so its start-up text never
# reaches vm.js's stdout while frames are still written.
sh "$(dirname "$0")/reference.sh"
cd /app/doomgeneric/doomgeneric
sed -i '\|/\* Use the real syscall for stdout/stderr \*/|a\
      static char stdout_buffer[65536];\
      static unsigned long stdout_used = 0;\
      if (stdout_used + (unsigned long)arg3 <= sizeof stdout_buffer) {\
        for (unsigned long k = 0; k < (unsigned long)arg3; k++) stdout_buffer[stdout_used + k] = ((const char *)arg2)[k];\
        stdout_used += (unsigned long)arg3;\
        return arg3;\
      }\
      real_syscall6(syscall_num, arg1, (long)stdout_buffer, (long)stdout_used, 0, 0, 0);\
      stdout_used = 0;' my_stdlib.c
grep -q stdout_buffer my_stdlib.c || { rm -f /app/doomgeneric_mips; exit 1; }
make all && cp doomgeneric_mips ../..
