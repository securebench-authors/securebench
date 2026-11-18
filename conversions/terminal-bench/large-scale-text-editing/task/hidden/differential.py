"""Differential test of the Oracle's hand-written scans against upstream's regular
expressions, on random inputs built from the characters and words those
expressions treat specially. CONVERSION.md records the result.

It needs Python 3.13 (upstream's verifier interpreter), the SecureBench sources and
upstream's tests/test_outputs.py. Run it inside the baseline image with a memory
limit, from the repository root mounted at /repo:

    docker run --rm --network none --memory 2g -v $PWD:/repo:ro -e PYTHONPATH=/repo \\
      <baseline image> python3 -B /repo/conversions/terminal-bench/large-scale-text-editing/task/hidden/differential.py \\
      /repo/conversions/upstream/terminal-bench/large-scale-text-editing/tests/test_outputs.py <rounds>
"""

import importlib.util
import os
import re
import sys
import tempfile
from pathlib import Path
from random import Random

from securebench.core.errors import Rejected
from securebench.core.evidence import ArtifactEvidence, FileEvidence, FileStatus
from securebench.core.task import Parser
from securebench.evidence.parsers import parse


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


oracle = load("oracle", Path(__file__).with_name("oracle.py"))
upstream = load("upstream_tests", sys.argv[1])
ROUNDS = int(sys.argv[2])
rng = Random(0)

CHARS = list(
    ":0123456789,$%+-.!()_ \t\"'\\<>@/^*|=" "\u0663\u00a0\u3000\u2028\u0085\x1c\r"
    "rRedEasSoOuUcCpPlLiItTvVbBnNwWyYhHfFgGxXmMkKqQjJ" "\u017f\u0131\u0130\u212a\u00e9"
)
WORDS = [
    "r", "read", "source", "so", "e", "edit", "sp", "split", "vs", "vsplit", "tabe",
    "tabedit", "new", "vnew", "READ", "Sp", "\u017fo", "\u017fplit", "tab\u0130",
    "system(", "glob(", "expand(", "executable(", "filereadable(", "SYSTEM(",
    "function", "function !", "function\t!", "let", "let ", "LET\u3000", "eval", "eval (",
    "py", "lua", "perl", "ruby", "PY", ":", ":!", ",", ",$", "1,", ".,$", "%", "\\<CR>",
    "call setreg('a', \"", "call setreg(\"b\",'", "setreg('c',", ":%normal! @", ":%normal!",
    "\")", "')", "\n", "\r\n", "\" comment", ":wq", ":x",
]


def fragment(budget):
    pieces = []
    for _ in range(rng.randrange(budget)):
        if rng.random() < 0.4:
            pieces.append(rng.choice(WORDS))
        else:
            pieces.append(rng.choice(CHARS))
    return "".join(pieces)


def keystroke_string():
    return fragment(14)


def script_text():
    """A script mostly of near-valid lines, so that the whole-file check is reached."""
    lines = []
    for _ in range(rng.randrange(1, 10)):
        roll = rng.random()
        register = rng.choice("abcd")
        quote = rng.choice("'\"")
        if roll < 0.45:
            body = keystroke_string()
            close = rng.choice(["\")", "')", "\") ", ")", "\")|x"])
            prefix = rng.choice(["call setreg(", ":call setreg(", " call setreg(", "call  setreg("])
            lines.append(f"{prefix}'{register}',{rng.choice(['', ' ', '  ', chr(9)])}{quote}{body}{close}")
        elif roll < 0.65:
            lines.append(rng.choice([":%normal! @", ":%normal!  @", " :%normal! @", ":%normal!\t@"]) + register + rng.choice(["", " ", "x"]))
        elif roll < 0.75:
            lines.append(rng.choice([":wq", ":x", " :wq ", ":q", ":wq!"]))
        elif roll < 0.85:
            lines.append("\"" + fragment(6))
        else:
            lines.append(fragment(10))
    separator = rng.choice(["\n", "\n", "\r\n", "\r"])
    return separator.join(lines) + rng.choice(["", "\n", separator])


def complete_script():
    """A valid script, perturbed in one place, to reach the passing side often."""
    regs = []
    for register in "abc":
        regs.append(f"call setreg('{register}', \"{keystroke_string()}\")")
    lines = regs + [":%normal! @a", ":%normal! @b", ":%normal! @c", rng.choice([":wq", ":x"])]
    rng.shuffle(lines)
    if rng.random() < 0.5:
        index = rng.randrange(len(lines))
        lines.insert(index, fragment(8))
    return rng.choice(["\n", "\r\n"]).join(lines) + "\n"


def upstream_keystrokes_valid(text):
    return upstream._is_valid_keystroke_sequence(text)


def upstream_well_formed(path):
    upstream.APPLY_SCRIPT = path
    try:
        upstream.test_apply_macros_well_formed()
    except AssertionError:
        return False
    return True


def oracle_well_formed(data):
    try:
        value = parse(Parser.TEXT, data)
        found = FileEvidence("/app/apply_macros.vim", FileStatus.PRESENT, value, len(data), None, None)
    except Rejected:
        found = FileEvidence("/app/apply_macros.vim", FileStatus.UNPARSABLE, None, len(data), None, "rejected")
    return oracle.judge("script", None, ArtifactEvidence("script", (found,), ())).passed


def count_line():
    parts = ["KEYSTROKES a=", rng.choice(["1", "12", "\u0663", "", "x"]), " b=", rng.choice(["0", "7"]),
             " c=", rng.choice(["3", "33"]), " total=", rng.choice(["16", "4", "1" * 5000, ""])]
    if rng.random() < 0.3:
        parts.insert(rng.randrange(len(parts)), rng.choice([" ", "\n", "x"]))
    return "".join(parts)


def upstream_counts(line):
    m = re.match(r"^KEYSTROKES a=(\d+) b=(\d+) c=(\d+) total=(\d+)$", line)
    if not m:
        return None
    try:
        return tuple(map(int, m.groups()))
    except ValueError:
        return None


def main():
    mismatches = 0
    passes = {"keystrokes": 0, "scripts": 0, "complete": 0}
    directory = tempfile.mkdtemp(dir="/dev/shm")
    path = Path(directory) / "apply_macros.vim"
    for _ in range(ROUNDS):
        keys = keystroke_string()
        expected = upstream_keystrokes_valid(keys)
        passes["keystrokes"] += expected
        if oracle._is_valid_keystroke_sequence(keys) != expected:
            mismatches += 1
            print("keystrokes", repr(keys), expected)
        line = f"call setreg('a', {rng.choice(chr(39) + chr(34))}{keys}" + rng.choice(["\")", "')", "'"])
        match = re.search(r"setreg\(['\"][abc]['\"],\s*['\"]([^'\"]*)['\"]", line)
        if oracle._extract_keystrokes(line) != (match.group(1) if match else None):
            mismatches += 1
            print("extract", repr(line))
        for kind, text in (("scripts", script_text()), ("complete", complete_script())):
            data = text.encode("utf-8")
            if rng.random() < 0.02:
                data = b"\xef\xbb\xbf" + data
            path.write_bytes(data)
            expected = upstream_well_formed(path)
            passes[kind] += expected
            if oracle_well_formed(data) != expected:
                mismatches += 1
                print("script", repr(text), expected)
            tokens = re.findall(r"^\s*:%normal!\s+(\S+)", path.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
            normalized = data.decode("utf-8", "ignore").replace("\r\n", "\n").replace("\r", "\n")
            if oracle._normal_tokens(normalized) != tokens:
                mismatches += 1
                print("tokens", repr(text))
        line = count_line()
        if oracle._parse_counts(line) != upstream_counts(line):
            mismatches += 1
            print("counts", repr(line[:80]))
    os.remove(path)
    os.rmdir(directory)
    print(f"rounds={ROUNDS} mismatches={mismatches} upstream_passes={passes}")


main()
