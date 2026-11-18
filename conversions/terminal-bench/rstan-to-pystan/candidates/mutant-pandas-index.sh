#!/bin/sh
# The reference writing each result with pandas' to_csv, dropping the header
# but keeping pandas' default index column: every row becomes "<index>,<mean>".
# Upstream reads the first field of each row (and the text before the first
# comma for alpha and sigma), so it reads the index 0, 1, 2 instead of the
# means.
set -e
reference="$(dirname "$0")/reference.sh"
mutant=$(mktemp)
sed -e 's/f\.write(f"{alpha_post}\\n")/pd.Series([alpha_post]).to_csv(f, header=False)/' \
    -e 's/f\.write(f"{sigma_post}\\n")/pd.Series([sigma_post]).to_csv(f, header=False)/' \
    -e 's/for rho_val in rho_post:/pd.Series(rho_post).to_csv(f, header=False)/' \
    -e 's/for beta_val in beta_post:/pd.Series(beta_post).to_csv(f, header=False)/' \
    -e '/f\.write(f"{rho_val}\\n")/d' \
    -e '/f\.write(f"{beta_val}\\n")/d' "$reference" > "$mutant"
if [ "$(grep -c 'to_csv(f, header=False)' "$mutant")" -ne 4 ] || grep -q 'f\.write(f"{' "$mutant"; then
    echo "the edit did not apply" >&2
    exit 1
fi
sh "$mutant"
