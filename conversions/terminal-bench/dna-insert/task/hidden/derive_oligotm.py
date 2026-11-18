"""Derive hidden/oligotm.json by running primer3's real oligotm.

The upstream test only ever passes oligotm a prefix of `vector2` (the forward
annealed part) or the reverse complement of a suffix of `vector1` (the reverse
annealed part), each 15 to 45 nucleotides long: any other primer fails an
earlier assertion. So the melting temperatures of these 62 sequences are every
value the test can compute, and the Oracle looks them up instead of
reimplementing primer3's thermodynamics.

Run it the way the native verifier gets oligotm (Ubuntu 24.04's primer3
package), from the directory that holds this script:

    docker run --rm -v "$PWD":/hidden:ro alexgshaw/dna-insert:20251031 sh -c \
      'apt-get update -qq && apt-get install -y -qq primer3 python3 >/dev/null \
       && python3 /hidden/derive_oligotm.py' > oligotm.json
"""

import json
import subprocess
import sys
from pathlib import Path

# The flags and their order are those of calc_tm_oligotm in upstream's test.
FLAGS = ["-mv", "50", "-dv", "2", "-n", "0.8", "-d", "500", "-tp", "1", "-sc", "1"]


def rc(seq: str) -> str:
    return seq.translate(str.maketrans("atcg", "tagc"))[::-1]


def oligotm(seq: str) -> dict:
    result = subprocess.run(["oligotm", *FLAGS, seq], text=True, capture_output=True, check=False)
    return {"sequence": seq, "stdout": result.stdout, "tm": float(result.stdout.strip())}


def main() -> None:
    expected = json.loads((Path(__file__).parent / "expected.json").read_text())
    lengths = range(expected["anneal_min"], expected["anneal_max"] + 1)
    version = subprocess.run(
        ["dpkg-query", "-W", "-f", "${Version}", "primer3"], text=True, capture_output=True, check=True
    ).stdout
    table = {
        "primer3_package_version": version,
        "flags": FLAGS,
        "forward": {str(n): oligotm(expected["vector2"][:n]) for n in lengths},
        "reverse": {str(n): oligotm(rc(expected["vector1"][-n:])) for n in lengths},
    }
    json.dump(table, sys.stdout, indent=1)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
