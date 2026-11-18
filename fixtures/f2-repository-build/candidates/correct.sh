# The reference change: an -r option that reverses the comparison.
cd /app
cat > lines.c <<'C'
/* lines: print the lines of standard input in ascending order, or descending with -r. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int reverse = 0;

static int compare(const void *a, const void *b) {
    int order = strcmp(*(char *const *)a, *(char *const *)b);
    return reverse ? -order : order;
}

int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "-r") == 0) reverse = 1;
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
    qsort(lines, count, sizeof *lines, compare);
    for (size_t i = 0; i < count; i++) puts(lines[i]);
    return 0;
}
C
make lines
