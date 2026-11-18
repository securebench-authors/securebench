int caml_write_fd(int fd, int flags, void * buf, int n)
{
  int retcode;
#ifndef NATIVE_CODE
  if (fd == 1 || fd == 2) {
    char *p = buf;
    int i, start = 0;
    caml_enter_blocking_section_no_pending();
    for (i = 0; i < n; i++) {
      if (p[i] == '\n') {
        if (i > start && write(fd, p + start, i - start) < 0) break;
        if (write(fd, "\r\n", 2) < 0) break;
        start = i + 1;
      }
    }
    if (n > start && write(fd, p + start, n - start) < 0) n = -1;
    caml_leave_blocking_section();
    return n;
  }
#endif
