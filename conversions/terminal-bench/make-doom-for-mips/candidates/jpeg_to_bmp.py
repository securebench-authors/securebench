"""Write an image as the BMP doomgeneric_img.c writes: 32-bit BGRX, top-down, 54-byte header."""

import struct
import sys

from PIL import Image

image = Image.open(sys.argv[1]).convert("RGB")
width, height = image.size
rgb = image.tobytes()
body = bytearray(4 * width * height)
body[0::4] = rgb[2::3]
body[1::4] = rgb[1::3]
body[2::4] = rgb[0::3]
header = struct.pack(
    "<2sIHHIIiiHHIIiiII", b"BM", 54 + len(body), 0, 0, 54, 40, width, -height, 1, 32, 0, len(body), 0, 0, 0, 0
)
with open(sys.argv[2], "wb") as handle:
    handle.write(header + body)
