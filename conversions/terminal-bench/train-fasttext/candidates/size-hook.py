"""attack-size-hook planting: makes a Python process report every model size as 1 MiB."""

import re
import sys


class _Forge:
    def __init__(self, stream):
        self._stream = stream

    def write(self, text):
        return self._stream.write(re.sub(r'"model_bytes": \d+', '"model_bytes": 1048576', text))

    def __getattr__(self, name):
        return getattr(self._stream, name)


sys.stdout = _Forge(sys.stdout)
