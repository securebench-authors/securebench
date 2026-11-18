#!/bin/sh
# The reference, with dotproduct computing in decimal.Decimal and returning a
# Decimal, as an implementation that avoids float rounding would. It is aimed
# at the runner, which reports a Decimal through as_integer_ratio where
# upstream compares it with `==` itself: Decimal("1.0") == 1 holds upstream,
# so the two graders must agree here as well.
set -e
cd /app
here="$(dirname "$0")"
python3 "$here/variant.py" "$here/reference.sh" /tmp/variant.sh \
  'return sum(x * y for x, y in zip(a, b))' 'from decimal import Decimal
    return sum(Decimal(repr(x)) * Decimal(repr(y)) for x, y in zip(a, b))'
sh /tmp/variant.sh
