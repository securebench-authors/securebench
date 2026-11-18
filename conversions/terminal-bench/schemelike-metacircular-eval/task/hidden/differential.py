"""Differential test of the adapter's decoding and the Oracle's normalization.

Run inside the baseline image, with upstream's tests/ where upstream mounts it
and the pack's evaluation/ where SecureBench mounts it:

    docker run --rm --network none --memory 2g --cpus 1 -v <repo>:/repo:ro \
      -v <upstream task>/tests:/tests:ro \
      -v <repo>/conversions/terminal-bench/schemelike-metacircular-eval/task/evaluation:/.securebench/evaluation:ro \
      <baseline image> python3 -B \
      /repo/conversions/terminal-bench/schemelike-metacircular-eval/task/hidden/differential.py

The adapter reimplements how upstream's subprocess.run(..., text=True) decodes
the output, and the Oracle reimplements normalize_output. For edits of the
reference near those (a last "True" line, surrounding whitespace, "\\r"
newlines, long output, invalid UTF-8, a timeout), the verdict of upstream's test
logic on three programs is printed next to ours: the adapter's observation
judged by the Oracle. Upstream's verdict uses its own functions, as its test
does. The candidate scripts are compared with the real native harness by
campaign.py qualify instead.
"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path("/repo")
CONVERSION = REPO / "conversions/terminal-bench/schemelike-metacircular-eval"
TASK = CONVERSION / "task"
sys.path.insert(0, str(REPO))

from securebench.core.evidence import CaseEvidence, Ending, HostFacts, Observed  # noqa: E402


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


oracle = load("oracle", TASK / "hidden/oracle.py")
upstream = load("test_outputs", Path("/tests/test_outputs.py"))


class Resources:
    def read(self, relative_path: str) -> bytes:
        return (TASK / "hidden" / relative_path).read_bytes()

    def read_json(self, relative_path: str):
        return json.loads(self.read(relative_path))


def ours(check: str, case) -> tuple[bool, object]:
    ran = subprocess.run(
        ["python3", "-I", "/.securebench/evaluation/adapter.py", check],
        input=json.dumps(case.challenge).encode(),
        capture_output=True,
        timeout=300,
    )
    response = json.loads(ran.stdout)
    evidence = CaseEvidence(
        check, 0, "", HostFacts(Ending.RETURNED, 0, 0.0), Observed(response["observation"]), ()
    )
    judgment = oracle.judge(check, case.context, evidence)
    return judgment.passed, judgment.diagnostic


def native(check: str, case) -> bool:
    """Upstream's test_interp for one program, verbatim in its logic."""
    challenge = case.challenge
    name, given = challenge["name"], challenge["input"] or None
    with tempfile.TemporaryDirectory() as directory:
        direct_dir, eval_dir = Path(directory, "direct"), Path(directory, "eval")
        direct_dir.mkdir()
        eval_dir.mkdir()
        for target in (direct_dir, eval_dir):
            for source in ("/app/interp.py", "/app/eval.scm"):
                if os.path.exists(source):
                    shutil.copy2(source, target)
            (target / name).write_text(challenge["program"], encoding="utf-8")
        try:
            os.chdir(direct_dir)
            direct_out, direct_err, direct_code = upstream.run_scheme_direct(name, given)
            os.chdir(eval_dir)
            eval_out, eval_err, _ = upstream.run_scheme_through_eval(name, given)
            eval2_out = eval_out
            if check == "twice":
                eval2_out, _, _ = upstream.run_scheme_through_eval(name, given, metacirc=True)
        except UnicodeDecodeError:
            return False
        finally:
            os.chdir("/")
    if direct_err == "TIMEOUT" or eval_err == "TIMEOUT":
        return False
    if direct_code != 0 and direct_code != -1:
        return False
    return (
        upstream.compare_outputs(direct_out, eval_out, name)[0]
        and upstream.compare_outputs(direct_out, eval2_out, name)[0]
    )


def reset_app() -> None:
    for entry in Path("/app").iterdir():
        shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
    shutil.copy2("/tests/interp.py", "/app/interp.py")
    shutil.copytree("/tests/test", "/app/test")


def reference_text() -> str:
    script = (CONVERSION / "candidates/reference.sh").read_text(encoding="utf-8")
    return script.split("cat <<'EOF' > eval.scm\n", 1)[1].rsplit("EOF\n", 1)[0]


def edit(transform):
    def write() -> None:
        reset_app()
        Path("/app/eval.scm").write_text(transform(reference_text()), encoding="utf-8")

    return write


NEWLINE = "(define-var! 'newline (make-primitive (lambda (args) (newline) #f)) initial-env)"
EDITS = {
    "edit-true-line": (lambda t: t + "(display #t)\n", True),
    "edit-two-true-lines": (lambda t: t + "(newline)\n(display #t)\n(newline)\n(display #t)\n", False),
    "edit-padded-true": (lambda t: t + '(newline)\n(display " True ")\n', False),
    "edit-leading-blank": (lambda t: '(display "   ")\n(newline)\n(newline)\n' + t, True),
    "edit-crlf": (lambda t: t.replace(NEWLINE, NEWLINE.replace("(newline) #f", "(putchr 13) (newline) #f")), True),
    "edit-cr": (lambda t: t.replace(NEWLINE, NEWLINE.replace("(newline) #f", "(putchr 13) #f")), True),
    "edit-long-whitespace": (lambda t: t + '(display "' + " " * 20000 + '")\n(newline)\n', True),
    "edit-long-output": (lambda t: t + '(display "' + "x" * 20000 + '")\n', False),
    "edit-invalid-utf8": (lambda t: t + "(putchr 56448)\n", False),
    "edit-timeout": (
        lambda t: "(define (fib n) (if (< n 2) n (+ (fib (- n 1)) (fib (- n 2)))))\n(fib 32)\n" + t,
        False,
    ),
}
def part_verdicts() -> None:
    plan = oracle.plan(Resources(), 0)
    few_labels = {"test/calculator.scm", "test/closures.scm", "test/06-interactive-io.scm"}
    few = [case for case in plan.cases["once"] if case.context["program"] in few_labels]
    assert len(few) == 3
    for name, (transform, passes) in EDITS.items():
        edit(transform)()
        cases = few[:1] if name == "edit-timeout" else few
        disagree = []
        mine_passed = theirs_passed = 0
        for case in cases:
            mine, _ = ours("once", case)
            with contextlib.redirect_stdout(io.StringIO()):
                theirs = native("once", case)
            mine_passed += mine
            theirs_passed += theirs
            if mine != theirs:
                disagree.append(f"{case.context['program']}: ours {mine}, native {theirs}")
        print(
            f"{name} (designed to {'pass' if passes else 'fail'}): passes of {len(cases)} cases:"
            f" ours {mine_passed}, native {theirs_passed}"
        )
        for line in disagree:
            print(f"  differs: {line}")


assert Path("/.securebench/evaluation/interp.py").read_bytes() == Path("/tests/interp.py").read_bytes()
print("evaluation/interp.py is upstream's tests/interp.py byte for byte")
part_verdicts()
