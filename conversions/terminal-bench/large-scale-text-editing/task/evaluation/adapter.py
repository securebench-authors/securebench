"""Adapter for the `run` check of large-scale-text-editing.

It repeats, in order, what upstream's `tests/test.sh` and the three running tests of
`tests/test_outputs.py` do on the candidate (`test_apply_macros_runs`,
`test_input_equiv_expected`, `test_macros_nonempty_and_efficient`), and reports the
values those tests assert on. It holds no expected value: the expected digest of the
transformed file stays on the host, and the Oracle does every comparison.

The candidate's Vim script can run shell commands, so everything after the first Vim
run is candidate-controlled; the Oracle treats the observation accordingly.
"""

import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

WORKDIR = Path("/app")
APPLY_SCRIPT = Path("/app/apply_macros.vim")
INPUT = Path("/app/input.csv")
DEFS_SCRIPT = Path("/app/_defs_only.vim")
KEYSTROKES_OUT = Path("/app/vim_keystrokes.out")
REGS_OUT = Path("/app/vim_regs.out")
GENERATOR = Path("/.securebench/evaluation/gen_large_csv.py")

# The same interpreter invocation as the check's command (brief 4.3): the stock
# image's loader, because `sys.executable` alone does not find its libraries.
STOCK = "/.securebench/python"
PYTHON = [
    f"{STOCK}/lib64/ld-linux-x86-64.so.2",
    "--library-path",
    f"{STOCK}/usr/local/lib:{STOCK}/lib/x86_64-linux-gnu:{STOCK}/usr/lib/x86_64-linux-gnu",
    f"{STOCK}/usr/local/bin/python3",
    "-I",
]

# The bound on the two dump files Vim writes. Honest dumps are a few hundred bytes;
# larger files are reported truncated and the Oracle fails them.
MAX_DUMP_CHARS = 65536


def run(cmd, timeout):
    """Run `cmd` like upstream's `_run`, reporting a timeout instead of raising."""
    try:
        done = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"returncode": 0, "timed_out": True}
    return {"returncode": done.returncode, "timed_out": False}


def regenerate_input():
    """`rm *.csv` and `python3 gen_large_csv.py input` in the working directory, as test.sh does."""
    for name in glob.glob("*.csv"):
        try:
            os.remove(name)
        except OSError:
            pass
    run([*PYTHON, str(GENERATOR), "input"], timeout=600)


def input_digest():
    """`INPUT.exists()` and `_sha256(INPUT)` from `test_input_equiv_expected`."""
    if not INPUT.exists():
        return "absent", ""
    try:
        digest = hashlib.sha256()
        with INPUT.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError:
        return "unreadable", ""
    return "read", digest.hexdigest()


def write_defs_only_script(src, out):
    """Upstream's `_write_defs_only_script`, unchanged."""
    text = src.read_text(encoding="utf-8", errors="ignore")
    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip() and not line.strip().startswith('"')
    ]
    setreg_lines = []
    for line in lines:
        if (re.match(r"^:?call setreg\(['\"][abc]['\"],", line) and
            (line.endswith("')") or line.endswith('")'))):
            setreg_lines.append(line)
    defs = setreg_lines
    extra = [
        "",
        '" Keystroke + content dump (normalized via keytrans)',
        "function! Count(reg) abort",
        "  let s = keytrans(getreg(a:reg))",
        "  let s = substitute(s, '<[^>]\\+>', \"\\x01\", 'g')",
        "  return strlen(s)",
        "endfunction",
        "let ra = keytrans(getreg('a'))",
        "let rb = keytrans(getreg('b'))",
        "let rc = keytrans(getreg('c'))",
        "let ka = Count('a')",
        "let kb = Count('b')",
        "let kc = Count('c')",
        "let kt = ka + kb + kc",
        "call writefile([printf('KEYSTROKES a=%d b=%d c=%d total=%d', ka, kb, kc, kt)],"
        "'/app/vim_keystrokes.out', 'w')",
        "call writefile([ra, rb, rc], '/app/vim_regs.out', 'w')",
        "qa!",
    ]
    out.write_text("\n".join(defs + extra), encoding="utf-8")


def read_dump(path):
    """Read a dump file as upstream does (`read_text(encoding="utf-8", errors="ignore")`)."""
    if not path.exists():
        return {"present": False, "text": "", "truncated": False}
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, ValueError):
        return {"present": False, "text": "", "truncated": False}
    return {
        "present": True,
        "text": text[:MAX_DUMP_CHARS],
        "truncated": len(text) > MAX_DUMP_CHARS,
    }


def main():
    sys.stdin.read()
    os.chdir(WORKDIR)
    regenerate_input()

    # test_apply_macros_runs
    vim = run(["vim", "-Nu", "NONE", "-n", "-Es", str(INPUT), "-S", str(APPLY_SCRIPT)], timeout=600)

    # test_input_equiv_expected
    input_kind, input_sha256 = input_digest()

    # test_macros_nonempty_and_efficient; it reads the script again after Vim ran it.
    try:
        write_defs_only_script(APPLY_SCRIPT, DEFS_SCRIPT)
        defs_written = True
    except (OSError, ValueError):
        defs_written = False
    if defs_written:
        defs = run(["vim", "-Nu", "NONE", "-n", "-Es", "-S", str(DEFS_SCRIPT)], timeout=300)
    else:
        defs = {"returncode": 0, "timed_out": False}

    observation = {
        "vim_returncode": vim["returncode"],
        "vim_timed_out": vim["timed_out"],
        "input_kind": input_kind,
        "input_sha256": input_sha256,
        "defs_written": defs_written,
        "defs_returncode": defs["returncode"],
        "defs_timed_out": defs["timed_out"],
        "keystrokes": read_dump(KEYSTROKES_OUT),
        "registers": read_dump(REGS_OUT),
    }
    sys.stdout.write(json.dumps({"observation": observation}))


main()
