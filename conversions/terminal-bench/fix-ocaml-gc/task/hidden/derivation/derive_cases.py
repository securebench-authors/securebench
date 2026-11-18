"""Derive hidden/cases.json and hidden/reference/ from one native run of the basic testsuite.

This script is not used at grading time. It records how the plan in cases.json
was obtained, so that a reviewer can redo it (see CONVERSION.md, "How the plan
was derived").

Inputs, all produced by building the reference solution in the upstream image and running

    cd /app/ocaml && strace -f -qq -v -s 8192 -e trace=execve,chdir,clone,clone3,vfork,fork \
        -e signal=none -o strace.txt \
        make -C testsuite one DIR=tests/basic OCAMLTESTFLAGS=-keep-test-dir-on-success

  argv[1]  strace.txt: the exact argv and working directory of every command ocamltest ran
  argv[2]  a copy of testsuite/tests/basic/_ocamltest/tests/basic (only the *.log files are read):
           which reference file each check compared with, and which source modules each
           build directory received
  argv[3]  testsuite/tests/basic from the upstream image: the test sources and reference files
  argv[4]  the hidden/ directory to write

Usage: python3 -I -B derive_cases.py strace.txt logs/ tests/basic/ hidden/
"""

import ast
import json
import os
import posixpath
import re
import shutil
import sys

OCAMLTEST_ROOT = "/app/ocaml/testsuite/tests/basic/_ocamltest/tests/basic"
SOURCE_DIR = "/app/ocaml/testsuite/tests/basic"
SUMMARY_LINE = "40 tests passed"
# tools/cmpbyt rejects a program whose trailer does not carry the exec magic number
# of the build (Config.exec_magic_number; configure derives it from
# build-aux/ocaml_version.m4, MAGIC_NUMBER__VERSION 037, in the upstream image).
EXEC_MAGIC = "Caml1999X037"


def ocamltest_children(strace_path):
    """Return [(test file, argv, cwd)] for every process ocamltest started, in order."""
    with open(strace_path, encoding="utf-8") as handle:
        lines = [line.rstrip("\n") for line in handle]
    # First pass: who forked whom. strace may print a child's first call before
    # the parent's clone returns, so the tree is built before cwd is tracked.
    parent = {}
    for raw in lines:
        match = re.match(r"^(\d+) (clone\(|<\.\.\. clone resumed>|vfork\(|fork\().*= (\d+)$", raw)
        if match:
            parent[int(match.group(3))] = int(match.group(1))
    cwd, pending, execs = {}, {}, {}
    for raw in lines:
        match = re.match(r"^(\d+) (.*)$", raw)
        if not match:
            continue
        pid, rest = int(match.group(1)), match.group(2)
        if pid not in cwd:
            cwd[pid] = cwd[parent[pid]] if pid in parent else "/app/ocaml"
        if rest.startswith("execve("):
            call = re.match(r'execve\((".*?"), (\[.*?\]), ', rest)
            argv = ast.literal_eval(call.group(2))
            if rest.endswith("<unfinished ...>"):
                pending[pid] = argv
            elif rest.rstrip().endswith("= 0"):
                execs.setdefault(pid, []).append((argv, cwd[pid]))
        elif rest.startswith("<... execve resumed>"):
            if rest.strip().endswith("= 0"):
                execs.setdefault(pid, []).append((pending[pid], cwd[pid]))
            pending.pop(pid, None)
        elif rest.startswith("chdir("):
            target = ast.literal_eval(re.match(r'chdir\((".*?")\)', rest).group(1))
            if rest.strip().endswith("= 0"):
                cwd[pid] = posixpath.normpath(posixpath.join(cwd[pid], target))
    ocamltest = {}
    for pid, calls in execs.items():
        argv = calls[-1][0]
        if argv[0].endswith("ocamltest.opt") and argv[-1].startswith("tests/basic/"):
            ocamltest[pid] = posixpath.basename(argv[-1])
    children = []
    for pid in sorted(execs):
        if parent.get(pid) in ocamltest:
            argv, where = execs[pid][-1]
            children.append((ocamltest[parent[pid]], argv, where))
    return children


def log_facts(log_path):
    """Source modules and the (output, reference) pairs ocamltest compared, in order."""
    modules, comparisons = None, []
    with open(log_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line.startswith("Source modules: "):
                modules = line[len("Source modules: "):].split()
            match = re.match(r"^Comparing (compiler|program) output (\S+) to reference (\S+)$", line)
            if match:
                comparisons.append((match.group(1), match.group(2), match.group(3)))
    return modules, comparisons


def expected_compiler_status(source_path, build_dir):
    """The test header may set `<compiler>_exit_status`; ocamltest expects 0 otherwise."""
    variable = posixpath.basename(build_dir).replace(".", "_") + "_exit_status"
    with open(source_path, encoding="utf-8") as handle:
        header = handle.read()
    match = re.search(variable + r'\s*=\s*"(\d+)"', header)
    return int(match.group(1)) if match else 0


def main():
    strace_path, logs_dir, sources_dir, hidden_dir = sys.argv[1:5]
    children = ocamltest_children(strace_path)
    steps, expectations, references = [], [], set()
    by_test = {}
    for test, argv, where in children:
        by_test.setdefault(test, []).append((argv, where))

    for test in sorted(by_test):
        stem = test[: -len(".ml")] if test.endswith(".ml") else test.replace(".ml.c", ".ml")
        modules, comparisons = log_facts(os.path.join(logs_dir, stem, stem + ".log"))
        compiler_checks = [c for c in comparisons if c[0] == "compiler"]
        program_checks = [c for c in comparisons if c[0] == "program"]
        linked = set()
        expect_runs = 0
        for index, (argv, where) in enumerate(by_test[test]):
            step_id = f"{stem}/{index}"
            if where not in linked:
                linked.add(where)
                steps.append({"id": f"{stem}/link-{len(linked)}", "op": "link", "dir": where, "names": modules})
            tool = posixpath.basename(argv[1]) if argv[0].endswith("ocamlrun") and len(argv) > 1 else posixpath.basename(argv[0])
            if tool == "cmpbyt":
                left, right = argv[2], argv[3]
                steps.append({"id": step_id + "-left", "op": "toc", "path": left})
                steps.append({"id": step_id + "-right", "op": "toc", "path": right})
                expectations.append({"kind": "same_bytecode", "left": step_id + "-left", "right": step_id + "-right",
                                     "magic": EXEC_MAGIC,
                                     "what": f"{test}: compare-bytecode-programs"})
            elif tool == "expect":
                steps.append({"id": step_id, "op": "exec", "dir": where, "argv": argv, "env": "compiler"})
                expectations.append({"kind": "exit", "step": step_id, "returncode": 0, "what": f"{test}: run-expect {argv[-1]}"})
                expect_runs += 1
                if expect_runs == 2:
                    kind, output, reference = program_checks.pop(0)
                    read_id = step_id + "-corrected"
                    steps.append({"id": read_id, "op": "read", "path": posixpath.join(where, output)})
                    name = posixpath.basename(reference)
                    references.add(name)
                    expectations.append({"kind": "text", "step": read_id, "reference": name,
                                         "what": f"{test}: check-program-output (expect)"})
            elif tool in ("ocamlc", "ocamlopt", "ocamlc.opt", "ocamlopt.opt"):
                output = posixpath.join(where, posixpath.basename(where) + ".output")
                kind, logged_output, reference = compiler_checks.pop(0)
                assert logged_output == output, (logged_output, output)
                steps.append({"id": step_id, "op": "exec", "dir": where, "argv": argv, "env": "compiler", "output": output})
                status = expected_compiler_status(os.path.join(sources_dir, test), where)
                expectations.append({"kind": "exit", "step": step_id, "returncode": status,
                                     "what": f"{test}: {posixpath.basename(where)}"})
                name = posixpath.basename(reference)
                if os.path.exists(os.path.join(sources_dir, name)):
                    references.add(name)
                    expectations.append({"kind": "text", "step": step_id, "reference": name,
                                         "what": f"{test}: check-{posixpath.basename(where)}-output"})
                else:
                    expectations.append({"kind": "empty", "step": step_id,
                                         "what": f"{test}: check-{posixpath.basename(where)}-output (no {name})"})
            elif argv[0].startswith(OCAMLTEST_ROOT) and len(argv) == 1:
                output = argv[0] + ".output"
                kind, logged_output, reference = program_checks.pop(0)
                assert logged_output == output, (logged_output, output)
                steps.append({"id": step_id, "op": "exec", "dir": where, "argv": argv, "env": "program", "output": output})
                expectations.append({"kind": "exit", "step": step_id, "returncode": 0, "what": f"{test}: run {posixpath.basename(argv[0])}"})
                name = posixpath.basename(reference)
                references.add(name)
                expectations.append({"kind": "text", "step": step_id, "reference": name,
                                     "what": f"{test}: check-program-output {posixpath.basename(argv[0])}"})
            else:
                raise SystemExit(f"unclassified command for {test}: {argv}")
        assert not compiler_checks and not program_checks, (test, compiler_checks, program_checks)

    os.makedirs(os.path.join(hidden_dir, "reference"), exist_ok=True)
    for name in sorted(references):
        shutil.copyfile(os.path.join(sources_dir, name), os.path.join(hidden_dir, "reference", name))
    cases = {
        "summary": {"dir": "/app/ocaml", "argv": ["make", "-C", "testsuite", "one", "DIR=tests/basic"],
                    "expected_substring": SUMMARY_LINE},
        "steps": steps,
        "expectations": expectations,
        "references": sorted(references),
        "tests": sorted(by_test),
    }
    with open(os.path.join(hidden_dir, "cases.json"), "w", encoding="utf-8") as handle:
        json.dump(cases, handle, indent=1)
        handle.write("\n")
    print(f"{len(by_test)} tests, {len(steps)} steps, {len(expectations)} expectations, {len(references)} references")


if __name__ == "__main__":
    main()
