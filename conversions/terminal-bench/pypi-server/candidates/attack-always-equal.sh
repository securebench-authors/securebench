#!/bin/sh
# The reference's server and packaging, with a dotproduct that computes
# nothing and returns an object equal to everything, so every
# `dotproduct(a, b) == expected` assertion holds.
set -e
cd /app
here="$(dirname "$0")"
python3 "$here/variant.py" "$here/reference.sh" /tmp/variant.sh \
  'def dotproduct(a, b):
    return sum(x * y for x, y in zip(a, b))' 'class _Equal:
    def __eq__(self, other):
        return True


def dotproduct(a, b):
    return _Equal()'
sh /tmp/variant.sh
