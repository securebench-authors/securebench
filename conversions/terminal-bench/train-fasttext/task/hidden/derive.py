"""Derive the evaluation reviews and the hidden labels from the upstream private test set.

Not part of the Oracle; kept so a reviewer can redo the derivation:

    python3 -I derive.py <upstream>/tests/private_test.tar.gz <pack>

Upstream's test_accuracy reads /tests/private_test.txt in text mode as UTF-8,
splits each stripped line at its first space into a label and a text, skips
lines without both, and passes the text to `model.predict`. This script does
the same and writes:

- `<pack>/evaluation/reviews.txt.gz`: the texts, one per line, in file order;
- `<pack>/hidden/labels.json`: the labels, in the same order.
"""

import gzip
import io
import json
import sys
import tarfile
from pathlib import Path

MEMBER = "private_test.txt"


def main() -> int:
    archive, pack = Path(sys.argv[1]), Path(sys.argv[2])
    with tarfile.open(archive, "r:gz") as tar:
        member = tar.extractfile(MEMBER)
        if member is None:
            raise SystemExit(f"{MEMBER} is not a regular file in {archive}")
        data = member.read()
    labels: list[str] = []
    texts: list[bytes] = []
    for line in io.TextIOWrapper(io.BytesIO(data), encoding="utf-8"):
        parts = line.strip().split(" ", 1)
        if len(parts) == 2:
            if "\n" in parts[1]:
                raise SystemExit("a text contains a newline")
            labels.append(parts[0])
            texts.append(parts[1].encode("utf-8"))
    reviews = b"".join(text + b"\n" for text in texts)
    (pack / "evaluation" / "reviews.txt.gz").write_bytes(gzip.compress(reviews, 9, mtime=0))
    (pack / "hidden" / "labels.json").write_text(json.dumps(labels) + "\n")
    print(f"{len(labels)} reviews")
    return 0


if __name__ == "__main__":
    sys.exit(main())
