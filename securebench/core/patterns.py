"""Exclude patterns (task format Section 6).

A pattern is a canonical relative path matched one component at a time against
a path relative to its scope root. A component `**` matches zero or more whole
components; elsewhere `*` matches zero or more characters within a component.
`?`, `[`, `]` and `\\` are rejected. A pattern that matches a path also matches
everything below it. Matching uses folded components.
"""

from securebench.core import paths
from securebench.core.errors import Rejected

MAX_PATTERNS = 256
_FORBIDDEN = frozenset("?[]\\")


def check_pattern(pattern: str) -> str:
    """Return `pattern` if it is valid; else raise `Rejected`."""
    paths.check_relative(pattern)
    if _FORBIDDEN & set(pattern):
        raise Rejected(f"exclude pattern {pattern!r} uses a character other than '*' specially")
    if all(part == "**" for part in paths.components(pattern)):
        raise Rejected(f"exclude pattern {pattern!r} would exclude the whole root")
    return pattern


def matches(pattern: str, relative_path: str) -> bool:
    """True when `pattern` matches `relative_path` or one of its ancestors."""
    pattern_parts = [paths.fold(part) for part in paths.components(pattern)]
    path_parts = [paths.fold(part) for part in paths.components(relative_path)]
    # reachable[j] is true when the pattern parts consumed so far match path_parts[:j].
    reachable = [True] + [False] * len(path_parts)
    for part in pattern_parts:
        following = [False] * (len(path_parts) + 1)
        for j, ok in enumerate(reachable):
            if not ok:
                continue
            if part == "**":
                for k in range(j, len(path_parts) + 1):
                    following[k] = True
                break
            if j < len(path_parts) and _component_matches(part, path_parts[j]):
                following[j + 1] = True
        reachable = following
    return any(reachable[1:])


def is_excluded(
    root_exclude: tuple[str, ...], git_directories: tuple[str, ...], relative_path: str
) -> bool:
    """True when the path is excluded by the root's patterns or by the implicit `**/.git`.

    A path inside one of `git_directories` is not excluded by `**/.git`.
    """
    parts = paths.components(relative_path)
    allowed = {paths.components(directory) for directory in git_directories}
    for index, part in enumerate(parts):
        if paths.fold(part) == ".git" and parts[: index + 1] not in allowed:
            return True
    return any(matches(pattern, relative_path) for pattern in root_exclude)


def _component_matches(pattern: str, text: str) -> bool:
    """Match `*` wildcards within one component, greedily with backtracking to the last star."""
    p = t = 0
    star = -1
    resume = 0
    while t < len(text):
        if p < len(pattern) and pattern[p] == "*":
            star, resume = p, t
            p += 1
        elif p < len(pattern) and pattern[p] == text[t]:
            p += 1
            t += 1
        elif star >= 0:
            p = star + 1
            resume += 1
            t = resume
        else:
            return False
    while p < len(pattern) and pattern[p] == "*":
        p += 1
    return p == len(pattern)
