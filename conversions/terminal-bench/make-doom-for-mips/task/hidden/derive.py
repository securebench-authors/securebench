"""Derive the Oracle's hidden data for make-doom-for-mips from upstream's tests.

Run inside the baseline image, whose Pillow is 11.2.1, the version the native
verifier installs, so that reference.jpg decodes to the same pixels:

    docker run --rm --network none -v <hidden>:/out -v <upstream tests>:/in:ro \
      <baseline image> python3 -I /out/derive.py /in/reference.jpg /out

It writes:

- reference-rgb.zlib: reference.jpg as Pillow's convert("RGB") sees it,
  row-major RGB bytes, zlib-compressed. This is what upstream compares against.
- cases.json: upstream's one case. Its challenge is empty, because upstream's
  tests give vm.js no input. Its expected values are the literal of
  test_vm_execution's `expected_text` and the size of reference.jpg, which
  test_frame_bmp_similar_to_reference requires of the frame.
"""

import json
import sys
import zlib
from pathlib import Path

from PIL import Image

EXPECTED_TEXT = "I_InitGraphics: DOOM screen size: w x h: 320 x 200"


def main() -> None:
    jpeg_path, out = Path(sys.argv[1]), Path(sys.argv[2])
    reference = Image.open(jpeg_path).convert("RGB")
    width, height = reference.size
    (out / "reference-rgb.zlib").write_bytes(zlib.compress(reference.tobytes(), 9))
    case = {
        "challenge": {},
        "expected_text": EXPECTED_TEXT,
        "reference": "reference-rgb.zlib",
        "width": width,
        "height": height,
    }
    (out / "cases.json").write_text(json.dumps([case], indent=2) + "\n")


if __name__ == "__main__":
    main()
