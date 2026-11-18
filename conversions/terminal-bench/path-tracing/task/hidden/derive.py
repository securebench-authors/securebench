"""Derive hidden/original-rgb.zlib, the image upstream compares with.

Upstream's test_image_similarity compares with /app/image.ppm, which the image
build rendered with orig.c and which the baseline ships. Copy it out of the
pinned baseline (the image of task.toml), with no network, then decode it:

    BASELINE=alexgshaw/path-tracing@sha256:4b44725102cd627dfa895191a5a30d16dae3c5623bb43da6459f79135db6b482
    mkdir -p out && docker run --rm --network none -v "$PWD/out:/out" "$BASELINE" \\
      cp /app/image.ppm /out/
    python3 derive.py out/image.ppm original-rgb.zlib

The file is P3 with maxval 255, so its values are the RGB bytes Pillow decodes
(differential.py checks this with Pillow 11.2.1). We stored the decoded values,
2400 x 1800 x 3 bytes in row order, compressed with zlib level 9. The image.ppm
we used has SHA-256
26f6b85ba478f0c67cd78c25d010608215627e88d8f4af61a718ac6084552183, and the
upstream reference (candidates/reference.sh) writes a byte-identical file.
"""

import hashlib
import sys
import zlib
from pathlib import Path

WIDTH, HEIGHT = 2400, 1800


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
