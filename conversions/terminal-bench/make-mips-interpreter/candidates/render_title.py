#!/usr/local/bin/python3
"""Draw DOOM's first frame without running DOOM, for attack-replace-elf.

Prints the I_InitGraphics line and writes /tmp/frame.bmp as doomgeneric_img.c
does (32-bit, top-down), showing the TITLEPIC lump of /app/doom.wad through the
first palette of its PLAYPAL lump and gamma row 0 of doomgeneric's tables.c,
each pixel doubled. It follows whatever palette doom.wad holds.
"""

import struct

WIDTH, HEIGHT = 320, 200

with open("/app/doom.wad", "rb") as handle:
    wad = handle.read()
count, directory = struct.unpack_from("<ii", wad, 4)
lumps = {}
for index in range(count):
    position, size, raw = struct.unpack_from("<ii8s", wad, directory + 16 * index)
    lumps.setdefault(raw.rstrip(b"\0").decode("ascii"), wad[position : position + size])

patch = lumps["TITLEPIC"]
screen = bytearray(WIDTH * HEIGHT)
for x in range(WIDTH):
    (offset,) = struct.unpack_from("<I", patch, 8 + 4 * x)
    while patch[offset] != 0xFF:
        top, length = patch[offset], patch[offset + 1]
        for y in range(length):
            screen[(top + y) * WIDTH + x] = patch[offset + 3 + y]
        offset += length + 4

with open("/app/doomgeneric/doomgeneric/tables.c") as handle:
    tables = handle.read()
start = tables.index("gammatable[5][256]")
body = tables[tables.index("{", tables.index("{", start) + 1) + 1 :]
gamma = [int(token) for token in body.split("}")[0].replace("\n", " ").split(",") if token.strip()]

palette = lumps["PLAYPAL"][:768]
bgra = [
    bytes((gamma[palette[3 * i + 2]], gamma[palette[3 * i + 1]], gamma[palette[3 * i]], 0)) * 2
    for i in range(256)
]
pixels = bytearray()
for y in range(HEIGHT):
    row = b"".join(bgra[i] for i in screen[y * WIDTH : (y + 1) * WIDTH])
    pixels += row + row
header = struct.pack("<2sIII", b"BM", 54 + len(pixels), 0, 54)
header += struct.pack("<IiiHHIIiiII", 40, 2 * WIDTH, -2 * HEIGHT, 1, 32, 0, len(pixels), 0, 0, 0, 0)
print("I_InitGraphics: DOOM screen size: w x h: 320 x 200", flush=True)
with open("/tmp/frame.bmp", "wb") as handle:
    handle.write(header + pixels)
