"""Decode /tmp/frame.bmp the way upstream's test does, for the adapter.

Runs on the baseline's own Python 3.13 and Pillow 11.2.1, the versions upstream's
verifier installs, so the pixels are those `Image.open(frame).convert("RGB")`
gives upstream. It prints one JSON object: the size and the RGB bytes in base64,
or a problem. A frame of more pixels than the adapter reports is not converted.
"""

import base64
import json
import sys

from PIL import Image

MAX_PIXELS = 262144

try:
    image = Image.open(sys.argv[1])
    width, height = image.size
    if width * height > MAX_PIXELS:
        result: dict[str, object] = {"problem": "too_large"}
    else:
        rgb = image.convert("RGB").tobytes()
        result = {
            "width": width,
            "height": height,
            "rgb_b64": base64.b64encode(rgb).decode("ascii"),
        }
except Exception:  # Any failure of Pillow fails upstream's test in the same way.
    result = {"problem": "undecodable"}
print(json.dumps(result))
