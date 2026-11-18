"""Derive hidden/original-rgb.zlib, the image the original /app/mystery writes.

Upstream's test_image_similarity runs /app/mystery and compares with what it
writes. The `original` check requires the baseline's binary, whose SHA-256 is
in hidden/expected.json (written `sha256:<hex>`, as artifact evidence gives
it). The program reads no input, so its image is fixed.
In the pinned baseline (the image of task.toml), with no network, take the
binary's SHA-256, render the image once and decode it:

    BASELINE=alexgshaw/path-tracing-reverse@sha256:7911e42479d8f6d8af1248bc52442a0efbc5a33e3ecf535fdc20d252a2c64142
    docker run --rm --network none "$BASELINE" sha256sum /app/mystery
    mkdir -p out && docker run --rm --network none -v "$PWD/out:/out" "$BASELINE" \\
      sh -c 'cd /out && /app/mystery'
    python3 derive.py out/image.ppm original-rgb.zlib

The file is P3 with maxval 255, so its values are the RGB bytes Pillow decodes
(differential.py checks this with Pillow 11.2.1). We stored the decoded values,
800 x 600 x 3 bytes in row order, compressed with zlib level 9. The image.ppm we
used has SHA-256 0d115b98f899dbfafed4a3e57c62a7182d6639861bb73d6965ec956a27d94ea7,
and the binary 869eebc7779f565fafcaae5c4c366c8d86bd5d21d9a8d1389d34fc67c09911de.
"""

import hashlib
import sys
import zlib
from pathlib import Path

WIDTH, HEIGHT = 800, 600


def main() -> None:
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    data = source.read_bytes()
    print("image.ppm sha256", hashlib.sha256(data).hexdigest())
    magic, size, maxval, body = data.split(b"\n", 3)
    if magic != b"P3" or size != b"%d %d" % (WIDTH, HEIGHT) or maxval != b"255":
        raise SystemExit("unexpected header")
    values = [int(token) for token in body.split()]
    if len(values) != WIDTH * HEIGHT * 3 or not all(0 <= value <= 255 for value in values):
        raise SystemExit("unexpected pixel data")
    target.write_bytes(zlib.compress(bytes(values), 9))
    print("wrote", target)


main()
