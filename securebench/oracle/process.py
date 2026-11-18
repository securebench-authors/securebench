"""The Oracle runs in its own host process, one per attempt.

The process has a minimal environment, a fixed hash seed, no bytecode cache,
a memory limit it sets on itself (`worker.MAX_MEMORY_BYTES`) and a time bound
on every request. Messages are single JSON lines in both
directions, bounded in size. Standard error is discarded so it can never fill
and block the channel.
"""

import os
import selectors
import subprocess
import sys
import time
from types import TracebackType
from typing import IO, cast

from securebench.core import jsondata
from securebench.core.errors import HostError, Rejected
from securebench.core.evidence import Evidence, Judgment, Plan, evidence_to_json, plan_from_json
from securebench.core.jsondata import JsonValue
from securebench.core.task import Task

PLAN_TIMEOUT_SECONDS = 600
JUDGE_TIMEOUT_SECONDS = 60
MAX_PLAN_BYTES = 256 << 20
MAX_JUDGMENT_BYTES = 1 << 20
MAX_DIAGNOSTIC_BYTES = 64 << 10
# A result record holds a diagnostic four levels down (record, judged list,
# entry, judgment); a deeper one could not be recorded.
MAX_DIAGNOSTIC_DEPTH = jsondata.MAX_DEPTH - 4


class OracleError(Exception):
    """The Oracle raised, timed out or answered malformed data."""


class OracleProcess:
    """A running Oracle for one task. Use as a context manager."""

    def __init__(self, task: Task) -> None:
        self.task = task
        self.process: subprocess.Popen[bytes] | None = None

    def __enter__(self) -> "OracleProcess":
        self._start()
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self._stop()

    def plan(self, seed: int) -> Plan:
        """The Oracle's plan. Any failure is the task's fault: a `HostError` (attempt `invalid`)."""
        try:
            response = self._request(
                {"op": "plan", "seed": seed}, PLAN_TIMEOUT_SECONDS, MAX_PLAN_BYTES
            )
            return plan_from_json(response["plan"])
        except (OracleError, Rejected) as error:
            raise HostError(f"the Oracle's plan failed: {error}") from None

    def judge(self, check_id: str, context: JsonValue, evidence: Evidence) -> Judgment:
        """The Oracle's judgment of one check or case.

        An exception, timeout or malformed judgment becomes a failing judgment
        whose diagnostic says so.
        """
        request: JsonValue = {
            "op": "judge",
            "check": check_id,
            "context": context,
            "evidence": evidence_to_json(evidence),
        }
        try:
            response = self._request(request, JUDGE_TIMEOUT_SECONDS, MAX_JUDGMENT_BYTES)
            judgment = response["judgment"]
            if not isinstance(judgment, dict) or set(judgment) != {"diagnostic", "passed"}:
                raise OracleError("the judgment has the wrong shape")
            passed = judgment["passed"]
            if type(passed) is not bool:
                raise OracleError("the judgment's 'passed' is not a boolean")
            diagnostic = judgment["diagnostic"]
            if len(jsondata.encode(diagnostic)) > MAX_DIAGNOSTIC_BYTES:
                raise OracleError("the judgment's diagnostic is too large")
            if jsondata.depth(diagnostic) > MAX_DIAGNOSTIC_DEPTH:
                raise OracleError("the judgment's diagnostic is nested too deeply")
            return Judgment(passed, diagnostic)
        except OracleError as error:
            return Judgment(False, {"oracle_error": str(error)[:4000]})
        except Rejected as error:
            # Evidence is bounded so that this cannot happen; a context the
            # author nested too deeply still fails the check instead of the run.
            return Judgment(False, {"oracle_error": f"the request cannot be sent: {error.reason}"})

    def _start(self) -> None:
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-B",
                "-m",
                "securebench.oracle.worker",
                str(self.task.hidden_dir / "oracle.py"),
                str(self.task.hidden_dir),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=environment,
            cwd=self.task.hidden_dir,
        )

    def _stop(self) -> None:
        process = self.process
        self.process = None
        if process is None:
            return
        cast(IO[bytes], process.stdin).close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=30)
        cast(IO[bytes], process.stdout).close()

    def _request(self, request: JsonValue, timeout: float, bound: int) -> dict[str, JsonValue]:
        """One request and its single-line response; a broken Oracle is restarted afterwards."""
        if self.process is None:
            raise HostError("the Oracle process is not running")
        try:
            response = self._exchange(self.process, jsondata.encode(request), timeout, bound)
        except OracleError:
            self._stop()
            self._start()
            raise
        if "error" in response:
            raise OracleError(f"the Oracle raised: {response['error']}")
        return response

    def _exchange(
        self, process: subprocess.Popen[bytes], data: bytes, timeout: float, bound: int
    ) -> dict[str, JsonValue]:
        deadline = time.monotonic() + timeout
        stdin = cast(IO[bytes], process.stdin)
        stdout = cast(IO[bytes], process.stdout)
        try:
            stdin.write(data)
            stdin.flush()
        except BrokenPipeError:
            raise OracleError("the Oracle process exited") from None
        buffer = bytearray()
        with selectors.DefaultSelector() as selector:
            selector.register(stdout, selectors.EVENT_READ)
            while not buffer.endswith(b"\n"):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise OracleError(f"the Oracle did not answer within {timeout} s")
                if not selector.select(remaining):
                    continue
                chunk = os.read(stdout.fileno(), 1 << 16)
                if not chunk:
                    raise OracleError("the Oracle process exited")
                buffer += chunk
                if len(buffer) > bound + 1:
                    raise OracleError("the Oracle's answer is too large")
        try:
            value = jsondata.decode(bytes(buffer), bound + 1)
        except Rejected as error:
            raise OracleError(f"the Oracle's answer is malformed: {error.reason}") from None
        if not isinstance(value, dict) or len(value) != 1:
            raise OracleError("the Oracle's answer has the wrong shape")
        return value
