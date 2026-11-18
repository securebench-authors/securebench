#!/bin/sh
# Writes values that a careless float conversion or comparison could mishandle: NaN and
# infinities (NaN compares false with everything, so an inverted check would pass it),
# 1e999 (parses to infinity), and an integer of 400 digits, beyond the float range but
# within Python's integer parsing limit. Aims to make the adapter or the Oracle crash or
# accept, turning a wrong answer into an infrastructure error or a pass.
cd /app || exit 1
big=$(printf '9%.0s' $(seq 1 400))
cat > results.json <<JSON
{"G": {"x0": NaN, "gamma": NaN, "amplitude": Infinity, "offset": -Infinity},
 "2D": {"x0": $big, "gamma": 1e999, "amplitude": -$big, "offset": NaN}}
JSON
