/* lines: print the lines of standard input in ascending order. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int ascending(const void *a, const void *b) {
    return strcmp(*(char *const *)a, *(char *const *)b);
}

int main(void) {
    char **lines = NULL;
    size_t count = 0, capacity = 0;
    char *line = NULL;
    size_t size = 0;
    ssize_t length;
    while ((length = getline(&line, &size, stdin)) != -1) {
        if (length > 0 && line[length - 1] == '\n') line[length - 1] = '\0';
        if (count == capacity) {
            capacity = capacity ? capacity * 2 : 16;
            lines = realloc(lines, capacity * sizeof *lines);
        }
        lines[count++] = strdup(line);
    }
    qsort(lines, count, sizeof *lines, ascending);
    for (size_t i = 0; i < count; i++) puts(lines[i]);
    return 0;
}
