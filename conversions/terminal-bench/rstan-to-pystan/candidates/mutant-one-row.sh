#!/bin/sh
# The reference writing each vector's three posterior means on one
# comma-separated row instead of one per row, as the instructions ask
# ("3 numbers, one per row").
set -e
reference="$(dirname "$0")/reference.sh"
mutant=$(mktemp)
sed -e 's/f\.write(f"{rho_val}\\n")/f.write(f"{rho_val},")/' \
    -e 's/f\.write(f"{beta_val}\\n")/f.write(f"{beta_val},")/' "$reference" > "$mutant"
if [ "$(grep -c 'f\.write(f"{rho_val},")\|f\.write(f"{beta_val},")' "$mutant")" -ne 2 ]; then
    echo "the edit did not apply" >&2
    exit 1
fi
sh "$mutant"
