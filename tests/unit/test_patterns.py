"""Exclude pattern semantics (task format Section 6)."""

import pytest

from securebench.core import patterns
from securebench.core.errors import Rejected


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("tests", "tests", True),
        ("tests", "tests/a/b.py", True),
        ("tests", "src/tests", False),
        ("tests/*", "tests/a.py", True),
        ("tests/*", "tests", False),
        ("tests/*", "tests/a/b.py", True),
        ("*.py", "a.py", True),
        ("*.py", "src/a.py", False),
        ("**/*_test.go", "pkg/x/y_test.go", True),
        ("**/*_test.go", "y_test.go", True),
        ("**/*_test.go", "pkg/y.go", False),
        ("src/**/fixtures", "src/fixtures/a", True),
        ("src/**/fixtures", "src/a/b/fixtures", True),
        ("Tests", "tests/x", True),
        ("a*b*c", "aXbYc", True),
        ("a*b*c", "aXbY", False),
        ("*", "anything/below", True),
    ],
)
def test_matching(pattern: str, path: str, expected: bool) -> None:
    assert patterns.matches(patterns.check_pattern(pattern), path) is expected


@pytest.mark.parametrize("pattern", ["a?", "[ab]", "a\\b", "/abs", "a/../b", "**", "**/**", ""])
def test_invalid_patterns(pattern: str) -> None:
    with pytest.raises(Rejected):
        patterns.check_pattern(pattern)


def test_git_directories_are_excluded_unless_listed() -> None:
    assert patterns.is_excluded((), (), ".git/config")
    assert patterns.is_excluded((), (), "vendor/lib/.git/HEAD")
    assert patterns.is_excluded((), (), "vendor/.GIT/HEAD")
    assert not patterns.is_excluded((), (".git",), ".git/config")
    assert patterns.is_excluded((), (".git",), "sub/.git/config")
    assert not patterns.is_excluded(("tests",), (), "src/main.c")
    assert patterns.is_excluded(("tests",), (), "tests")


def test_matching_is_linear_enough_for_hostile_names() -> None:
    assert not patterns.matches("*a*a*a*a*a*a*b", "a" * 4000)
