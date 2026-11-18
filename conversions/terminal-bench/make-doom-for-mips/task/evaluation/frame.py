"""Open /tmp/frame.bmp the way upstream's tests do and print what was found, as JSON.

The adapter runs this with the baseline's own Python, /usr/local/bin/python3,
whose Pillow is 11.2.1, the version upstream's verifier installs. That Python
lies outside the scope, so every case starts with the baseline's copy.

test_frame_bmp_exists checks that the file exists and is not empty;
test_frame_bmp_similar_to_reference opens it with Image.open(...).convert("RGB").
This prints which of those steps failed, or the image's size and its pixels as
top-to-bottom rows of RGB hex. It compares nothing.
"""

import json
import os
import sys

from PIL import Image

FRAME = "/tmp/frame.bmp"
# Bounds on what the observation can carry. Every larger image also fails
# upstream's size check, which needs reference.jpg's 640x400.
MAX_SIDE = 4096
MAX_PIXELS = 262144


def describe(path: str) -> dict[str, object]:
    try:
        size = os.stat(path).st_size
    except FileNotFoundError:
        return {"problem": "absent"}
    except OSError:
        return {"problem": "unreadable"}
    if size == 0:
        return {"problem": "empty"}
    try:
        image = Image.open(path)
        width, height = image.size
        if width > MAX_SIDE or height > MAX_SIDE or width * height > MAX_PIXELS:
            return {"width": width, "height": height, "rows": []}
        rgb = image.convert("RGB").tobytes()
    except Exception:
        return {"problem": "unreadable"}
    stride = 3 * width
    rows = [rgb[y * stride : (y + 1) * stride].hex() for y in range(height)]
    return {"width": width, "height": height, "rows": rows}


if __name__ == "__main__":
    json.dump(describe(sys.argv[1] if len(sys.argv) > 1 else FRAME), sys.stdout)
