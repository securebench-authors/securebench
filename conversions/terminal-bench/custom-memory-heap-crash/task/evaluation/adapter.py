"""custom-memory-heap-crash adapter: build the program one way, run it, report what happened.

The argument names one upstream test: `debug` (test_debug_build_runs_without_crash),
`release` (test_release_build_runs_without_crash) or `valgrind`
(test_no_memory_leaks_with_valgrind). Like each of those tests, the adapter
compiles the build it needs with upstream's exact command, then runs it once.
Each check runs in its own fresh Evaluation environment, so no candidate code
has run before the build under test is compiled and run.

Assertion-free: it reports the compiler's exit status, whether its output was
valid UTF-8 (upstream captures it with `text=True`) and whether the executable
exists; then how the run ended, its exit status and whether its standard
output and standard error were valid UTF-8. The first 1 KiB of the compiler's
and the run's output is passed on for diagnostics only. The Oracle decides.
"""

import json
import os
import subprocess
import sys

MODE = sys.argv[1]
BUILD = "debug" if MODE == "debug" else "release"
EXECUTABLE = f"/app/{BUILD}"
# Upstream's compile_program, with g++ and valgrind named by absolute path: a
# file planted earlier on PATH outside the scope is not captured anyway.
FLAGS = {
    "debug": ["-g", "-O0", "-L/usr/local/gcc-custom-debug/lib64"],
    "release": ["-O2", "-DNDEBUG", "-L/usr/local/gcc-custom-release/lib64"],
}
COMPILE = [
    "/usr/bin/g++", "-std=c++17", "-o", EXECUTABLE, "/app/main.cpp", "/app/user.cpp",
    *FLAGS[BUILD], "-Wl,-Bstatic", "-lstdc++", "-Wl,-Bdynamic", "-lm",
]
# Upstream's Valgrind command plus --command-line-only=yes, so that a
# .valgrindrc planted in /app (the working directory, which upstream reads)
# cannot add suppressions or change the options.
RUN = {
    "debug": [EXECUTABLE],
    "release": [EXECUTABLE],
    "valgrind": [
        "/usr/bin/valgrind", "--command-line-only=yes", "--leak-check=full",
        "--error-exitcode=1", "--errors-for-leak-kinds=definite", "--quiet", EXECUTABLE,
    ],
}[MODE]
# Upstream's per-run timeouts: 10 s for a plain run, 30 s under Valgrind.
RUN_TIMEOUT = 30 if MODE == "valgrind" else 10
# Upstream sets no compile timeout; its verifier has 1,800 s in all.
COMPILE_TIMEOUT = 600
ENVIRONMENT = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
}
SHOWN = 1024


def run(argv: list[str], timeout: int) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(
            argv,
            cwd="/app",
            env=ENVIRONMENT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None


def utf8(*outputs: bytes) -> bool:
    try:
        for output in outputs:
            output.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def status(code: int) -> int:
    return max(-255, min(255, code))


json.loads(sys.stdin.buffer.read())
observation: dict[str, object] = {
    "compile_exit_status": 0,
    "compile_timed_out": False,
    "compile_utf8": True,
    "compile_output": "",
    "executable": False,
    "ran": False,
    "timed_out": False,
    "exit_status": 0,
    "utf8": True,
    "run_output": "",
}
compiled = run(COMPILE, COMPILE_TIMEOUT)
if compiled is None:
    observation["compile_timed_out"] = True
else:
    observation["compile_exit_status"] = status(compiled.returncode)
    observation["compile_utf8"] = utf8(compiled.stdout, compiled.stderr)
    shown = (compiled.stdout + compiled.stderr)[:SHOWN]
    observation["compile_output"] = shown.decode("utf-8", "replace")
    observation["executable"] = os.path.exists(EXECUTABLE)
    if compiled.returncode == 0 and observation["executable"]:
        observation["ran"] = True
        ran = run(RUN, RUN_TIMEOUT)
        if ran is None:
            observation["timed_out"] = True
        else:
            observation["exit_status"] = status(ran.returncode)
            observation["utf8"] = utf8(ran.stdout, ran.stderr)
            shown = (ran.stdout + ran.stderr)[:SHOWN]
            observation["run_output"] = shown.decode("utf-8", "replace")
print(json.dumps({"observation": observation}))
