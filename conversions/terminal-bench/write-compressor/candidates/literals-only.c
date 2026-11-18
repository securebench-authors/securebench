/* A correct encoder for /app/decomp.c's format that never uses back-references:
 * every byte of stdin becomes a literal token. Its output decompresses to the
 * input exactly but is too large for the 2500-byte limit. */
#include <stdio.h>
#include <stdlib.h>

#define RADIX 255
#define MAX_DIGITS 1000000

static unsigned char digits[MAX_DIGITS]; /* the low end of the interval, base 255, most significant first */
static long ndigits;
static long range = 1;
static int counts[2000000];

static void add_low(long amount) {
  long i = ndigits - 1;
  while (amount) {
    long v = digits[i] + amount;
    digits[i] = (unsigned char)(v % RADIX);
    amount = v / RADIX;
    i--;
  }
}

static void put_bit(int bit, int ctx) {
  if (range < RADIX) {
    range *= RADIX;
    digits[ndigits++] = 0;
  }
  int *c = counts + ctx * 2;
  long split = range * (c[0] + 1) / (c[0] + c[1] + 2);
  if (bit) {
    if (split == range) {
      fprintf(stderr, "bit 1 has no room\n");
      exit(1);
    }
    add_low(split);
    range -= split;
  } else {
    if (split == 0) {
      fprintf(stderr, "bit 0 has no room\n");
      exit(1);
    }
    range = split;
  }
  c[bit]++;
}

static void put_integer(long n, int off, int ctx) {
  long value = n + (1L << off);
  int length = 0;
  while ((value >> length) > 1) length++; /* bits below the leading one */
  ctx *= 99;
  int t = off;
  for (int z = length - off; z > 0; z--) put_bit(0, ++t + ctx);
  put_bit(1, ++t + ctx);
  for (int b = length - 1; b >= 0; b--) put_bit((int)((value >> b) & 1), ctx);
}

int main(void) {
  static unsigned char input[10000];
  size_t n = fread(input, 1, sizeof input, stdin);
  put_integer((long)n, 9, 0);
  for (size_t k = 0; k < n; k++) {
    put_bit(0, 1); /* literal, not a match */
    put_bit(0, 8); /* positive */
    put_integer(input[k], 4, 9);
  }
  for (long k = 0; k < ndigits; k++) putchar(digits[k] + 1);
  return 0;
}
