"""Checks the Oracle's oligotm reimplementation against primer3's own binary.

Not used during grading. Upstream's test only ever passes oligotm a substring
of 15 to 45 bases of a template (the doubled circular vector, egfp, flag or
snap), so this enumerates every such substring and compares the Oracle's
value with the native one, as the printed "%f" string.

Run from the repository root (`-B` keeps __pycache__ out of the pack):

    python3 -B .../hidden/check_oligotm.py domain > domain.txt
    docker run --rm --memory 1g -v "$PWD:/w" alexgshaw/dna-assembly:20251031 sh -c '
      apt-get update >/dev/null && apt-get install -y primer3 >/dev/null &&
      while read -r s; do
        printf "%s %s\n" "$s" "$(oligotm -tp 1 -sc 1 -mv 50 -dv 2 -n 0.8 -d 500 "$s")"
      done < /w/domain.txt > /w/native.txt'
    uv run python -B .../hidden/check_oligotm.py compare native.txt
"""

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def domain() -> list[str]:
    templates = json.loads((HERE / "templates.json").read_text())
    found: set[str] = set()
    for name in ("input", "egfp", "flag", "snap"):
        template = templates[name] * 2 if name == "input" else templates[name]
        for length in range(15, 46):
            for start in range(len(template) - length + 1):
                found.add(template[start : start + length])
    return sorted(found)


def compare(native_path: str) -> int:
    spec = importlib.util.spec_from_file_location("oracle", HERE / "oracle.py")
    assert spec is not None and spec.loader is not None
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    native = dict(line.split() for line in Path(native_path).read_text().splitlines())
    missing = set(domain()) - set(native)
    differ = [(s, v, oracle._oligotm(s)) for s, v in native.items() if v != f"{oracle._oligotm(s):.6f}"]
    for seq, want, got in differ[:10]:
        print(f"differs: {seq} native {want} oracle {got:.6f}")
    print(f"{len(native)} sequences compared, {len(missing)} missing, {len(differ)} differ")
    return 1 if missing or differ else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["domain"]:
        print("\n".join(domain()))
    elif len(sys.argv) == 3 and sys.argv[1] == "compare":
        sys.exit(compare(sys.argv[2]))
    else:
        sys.exit(__doc__)
