#!/bin/sh
# The reference with a progress bar on standard error: one byte 219 per row
# written, the full block of the old PC code page, which is not UTF-8. The
# image is exact, but upstream reads the run's output with `text=True`, which
# raises UnicodeDecodeError.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i 's/^}}fclose(fp);$/}fputc(219,stderr);}fclose(fp);/' image.c
grep -q '^}fputc(219,stderr);}fclose(fp);$' image.c || { rm -f image.c; exit 1; }
