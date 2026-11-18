"""The Oracle worker: `python -I -B -m securebench.oracle.worker <oracle.py> <hidden dir>`.

Limits its own memory, loads the Oracle with an import guard that admits only
the allowed modules, then answers `plan` and `judge` requests read from
standard input. Each request and each response is one JSON line.
"""

import builtins
import os
import resource
import stat
import sys
import traceback
import types
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import cast

from securebench.core import jsondata, paths
from securebench.core.errors import Rejected
from securebench.core.evidence import (
    Evidence,
    Judgment,
    Plan,
    evidence_from_json,
    plan_to_json,
)
from securebench.core.jsondata import JsonValue
from securebench.oracle.static import ALLOWED_MODULES, FORBIDDEN_NAMES, check_oracle_source

MAX_REQUEST_BYTES = 512 << 20
MAX_RESOURCE_BYTES = 1 << 30
# The Oracle's address space. Past it an allocation raises
# MemoryError, which fails the judgment instead of exhausting the host. The
# largest measured Oracle needs 1.7 GiB, and the largest evidence the framework
# lets through for one case decodes to about 1.9 GiB.
MAX_MEMORY_BYTES = 4 << 30


class Resources:
    """`HiddenResources` over the task's `hidden/` lane, which pack validation checked."""

    def __init__(self, hidden: Path) -> None:
        self.hidden = hidden

    def read(self, relative_path: str) -> bytes:
        paths.check_relative(relative_path)
        path = self.hidden / relative_path
        status = os.lstat(path)
        if not stat.S_ISREG(status.st_mode):
            raise Rejected(f"hidden resource {relative_path} is not a regular file")
        # Checked before reading: a read with a size reserves that much address
        # space up front, which the worker's memory limit counts.
        if status.st_size > MAX_RESOURCE_BYTES:
            raise Rejected(f"hidden resource {relative_path} is too large")
        return path.read_bytes()

    def read_json(self, relative_path: str) -> JsonValue:
        data = self.read(relative_path)
        return jsondata.decode(data, len(data))


def _guarded_import(
    name: str,
    globals: Mapping[str, object] | None = None,
    locals: Mapping[str, object] | None = None,
    fromlist: Sequence[str] = (),
    level: int = 0,
) -> types.ModuleType:
    allowed = name in ALLOWED_MODULES or (name == "random" and list(fromlist) == ["Random"])
    if level != 0 or not allowed:
        raise ImportError(f"import of {name} is not allowed in an Oracle")
    return __import__(name, globals, locals, fromlist, level)


def load(source_path: Path) -> types.ModuleType:
    source = source_path.read_text(encoding="utf-8")
    check_oracle_source(source, source_path.name)
    safe = {name: value for name, value in vars(builtins).items() if name not in FORBIDDEN_NAMES}
    safe["__import__"] = _guarded_import
    module = types.ModuleType("securebench_task_oracle")
    module.__dict__["__builtins__"] = safe
    sys.modules[module.__name__] = module
    exec(compile(source, str(source_path), "exec"), module.__dict__)
    return module


def serve(module: types.ModuleType, resources: Resources) -> None:
    plan = cast(Callable[[Resources, int], object], module.plan)
    judge = cast(Callable[[str, JsonValue, Evidence], object], module.judge)
    for line in sys.stdin.buffer:
        request = jsondata.decode(line, MAX_REQUEST_BYTES)
        assert isinstance(request, dict)
        try:
            if request["op"] == "plan":
                seed = request["seed"]
                assert type(seed) is int
                result = plan(resources, seed)
                if not isinstance(result, Plan):
                    raise TypeError("plan must return a Plan")
                response: JsonValue = {"plan": plan_to_json(result)}
            else:
                check_id = request["check"]
                assert isinstance(check_id, str)
                judgment = judge(
                    check_id, request["context"], evidence_from_json(request["evidence"])
                )
                if not isinstance(judgment, Judgment) or type(judgment.passed) is not bool:
                    raise TypeError("judge must return a Judgment with a boolean 'passed'")
                response = {
                    "judgment": {"diagnostic": judgment.diagnostic, "passed": judgment.passed}
                }
            encoded = jsondata.encode(response)
        except Exception as error:
            detail = "".join(traceback.format_exception_only(error)).strip()
            encoded = jsondata.encode({"error": detail[:4000]})
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()


def main() -> int:
    # The hard limit too, so that nothing in this process can raise it again.
    resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
    module = load(Path(sys.argv[1]))
    serve(module, Resources(Path(sys.argv[2])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
