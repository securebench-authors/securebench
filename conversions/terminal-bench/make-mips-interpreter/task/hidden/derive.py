"""Derive the Oracle's reference pixels for make-mips-interpreter.

Run inside the baseline image, whose Pillow is 11.2.1, the version the native
verifier installs, so that reference.jpg decodes to the same pixels:

    docker run --rm --network none -v <hidden>:/out -v <upstream tests>:/in:ro \
      <baseline image> python3 /out/derive.py /in/reference.jpg /out

It writes reference-rgb.zlib: upstream's tests/reference.jpg as Pillow's
convert("RGB") sees it, row-major RGB bytes, zlib-compressed. This is what
upstream's test_frame_bmp_similar_to_reference compares the frame with. It
prints the picture's size, which cases.json records as the expected size.
"""

import sys
import zlib
from pathlib import Path

from PIL import Image


def main() -> None:
    jpeg_path, out = Path(sys.argv[1]), Path(sys.argv[2])
    reference = Image.open(jpeg_path).convert("RGB")
    (out / "reference-rgb.zlib").write_bytes(zlib.compress(reference.tobytes(), 9))
    print(f"reference.jpg is {reference.size[0]}x{reference.size[1]}")


if __name__ == "__main__":
    main()
