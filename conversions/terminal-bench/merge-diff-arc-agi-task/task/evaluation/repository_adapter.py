"""Report what upstream's repository tests observe in /app/repo.

Upstream's test_git_repo_init checks that /app/repo/.git exists, and
test_both_bundles_fetched runs `git branch -a` in /app/repo and searches its
output for the branch names. Neither the baseline nor the Evaluation has git,
so this adapter reimplements the part of git 2.43 (the version upstream's
verifier installs on Ubuntu 24.04) that `git branch -a` reaches: repository
discovery, the repository format check, and listing refs/heads and
refs/remotes from loose and packed refs. CONVERSION.md lists what it leaves
out and how it was compared with the real git.

The adapter reports the output lines and the exit status; the Oracle decides.
"""

import json
import os
import sys

# git's own isspace (git-compat-util.h sane_ctype), not C's: \f and \v are
# not whitespace to git.
GIT_SPACE = b" \t\n\r"

REPO = "/app/repo"
SYMREF_MAXDEPTH = 5
GITFILE_MAX_BYTES = 1 << 20
V0_EXTENSIONS = {"noop", "preciousobjects", "partialclone", "worktreeconfig"}
V1_ONLY_EXTENSIONS = {"noop-v1", "objectformat", "compatobjectformat"}
MAX_LINES = 10000


class Fatal(Exception):
    """A condition on which git dies with exit status 128."""


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


def is_hex(data):
    return len(data) > 0 and all(c in b"0123456789abcdefABCDEF" for c in data)


def validate_headref(path):
    # setup.c validate_headref: a symlink into refs/, "ref:" + refs/..., or an
    # object id at the start of the file.
    try:
        if os.path.islink(path):
            return os.readlink(path).startswith("refs/")
        data = read_bytes(path)[:255]
    except OSError:
        return False
    if data.startswith(b"ref:"):
        if data[4:].lstrip(GIT_SPACE).startswith(b"refs/"):
            return True
    return is_hex(data[:40]) or is_hex(data[:64])


def read_trimmed_path_file(path):
    data = read_bytes(path)
    while data[-1:] in (b"\n", b"\r"):
        data = data[:-1]
    return os.fsdecode(data)


def common_dir(gitdir):
    try:
        target = read_trimmed_path_file(os.path.join(gitdir, "commondir"))
    except OSError:
        return gitdir
    return os.path.join(gitdir, target)


def is_git_directory(suspect):
    if not validate_headref(os.path.join(suspect, "HEAD")):
        return False
    common = common_dir(suspect)
    return os.access(os.path.join(common, "objects"), os.X_OK) and os.access(
        os.path.join(common, "refs"), os.X_OK
    )


def read_gitfile(path):
    """setup.c read_gitfile_gently: None when .git is not a regular file."""
    try:
        if not os.path.isfile(path):
            return None
    except OSError:
        return None
    if os.path.getsize(path) > GITFILE_MAX_BYTES:
        raise Fatal("gitfile too large")
    try:
        data = read_bytes(path)
    except OSError:
        raise Fatal("cannot read gitfile") from None
    if not data.startswith(b"gitdir: "):
        raise Fatal("invalid gitfile format")
    target = data[len(b"gitdir: ") :]
    while target[-1:] in (b"\n", b"\r"):
        target = target[:-1]
    if not target:
        raise Fatal("no path in gitfile")
    gitdir = os.path.join(os.path.dirname(path), os.fsdecode(target))
    if not is_git_directory(gitdir):
        raise Fatal("gitfile does not point to a repository")
    return gitdir


def discover(start):
    """setup.c setup_git_directory_gently_1 with die_on_error."""
    directory = start
    while True:
        dotgit = os.path.join(directory, ".git")
        gitdir = read_gitfile(dotgit)
        if gitdir is None and is_git_directory(dotgit):
            gitdir = dotgit
        if gitdir is not None:
            return gitdir
        if is_git_directory(directory):
            return directory
        if directory == "/":
            raise Fatal("not a git repository")
        directory = os.path.dirname(directory)


# --- git config, as far as the repository format check needs it -------------


def parse_config(data):
    """Return {lowercased "section.key": [values]}; raise Fatal on bad syntax.

    Follows the grammar of git's config.c: [section], [section "sub"],
    [section.sub], `key = value`, a bare `key` (no value), quotes, the escapes
    \\ \" \n \t \b, backslash-newline continuation, and # or ; comments.
    """
    text = data.decode("utf-8", "surrogateescape")
    text = text.replace("\r\n", "\n")
    if text.startswith("\ufeff"):
        text = text[1:]
    pos = 0
    section = ""
    values = {}

    def peek():
        return text[pos] if pos < len(text) else ""

    while pos < len(text):
        c = text[pos]
        if c in GIT_SPACE.decode():
            pos += 1
            continue
        if c in "#;":
            while pos < len(text) and text[pos] != "\n":
                pos += 1
            continue
        if c == "[":
            pos += 1
            name = ""
            while peek() and (peek().isascii() and (peek().isalnum() or peek() in "-.")):
                name += text[pos]
                pos += 1
            if peek() in (" ", "\t"):
                while peek() in (" ", "\t"):
                    pos += 1
                if peek() != '"':
                    raise Fatal("bad config section")
                pos += 1
                while peek() and peek() not in ('"', "\n"):
                    if peek() == "\\":
                        pos += 1
                    pos += 1
                if peek() != '"':
                    raise Fatal("bad config section")
                pos += 1
            if peek() != "]" or not name:
                raise Fatal("bad config section")
            pos += 1
            section = name.lower()
            continue
        if not (c.isascii() and c.isalpha()):
            raise Fatal("bad config line")
        key = ""
        while peek() and peek().isascii() and (peek().isalnum() or peek() == "-"):
            key += text[pos]
            pos += 1
        while peek() in (" ", "\t"):
            pos += 1
        if peek() in ("\n", ""):
            value = None
        elif peek() == "=":
            pos += 1
            value, pos = parse_value(text, pos)
        else:
            raise Fatal("bad config line")
        values.setdefault(f"{section}.{key.lower()}", []).append(value)
    return values


def parse_value(text, pos):
    out = []
    quoted = False
    pending_space = ""
    while pos < len(text):
        c = text[pos]
        pos += 1
        if c == "\n":
            if quoted:
                raise Fatal("unterminated quote")
            return "".join(out), pos
        if not quoted and c in "#;":
            while pos < len(text) and text[pos] != "\n":
                pos += 1
            continue
        if not quoted and c in " \t\r":
            if out:
                pending_space += c
            continue
        if pending_space:
            out.append(pending_space)
            pending_space = ""
        if c == "\\":
            if pos >= len(text):
                raise Fatal("bad escape")
            e = text[pos]
            pos += 1
            if e == "\n":
                continue
            escaped = {"t": "\t", "b": "\b", "n": "\n", "\\": "\\", '"': '"'}.get(e)
            if escaped is None:
                raise Fatal("bad escape")
            out.append(escaped)
            continue
        if c == '"':
            quoted = not quoted
            continue
        out.append(c)
    if quoted:
        raise Fatal("unterminated quote")
    return "".join(out), pos


def config_int(value):
    if value is None:
        raise Fatal("missing numeric value")
    # git_parse_signed: strtoimax with base 0, then an optional k, m or g.
    text = value.lstrip(" \t\n\r\f\v")
    factor = 1
    if text[-1:].lower() in ("k", "m", "g"):
        factor = {"k": 1 << 10, "m": 1 << 20, "g": 1 << 30}[text[-1].lower()]
        text = text[:-1]
    sign = -1 if text[:1] == "-" else 1
    body = text[1:] if text[:1] in ("+", "-") else text
    if body[:2].lower() == "0x" and len(body) > 2 and all(c in "0123456789abcdefABCDEF" for c in body[2:]):
        number = int(body[2:], 16)
    elif body.startswith("0") and all(c in "01234567" for c in body):
        number = int(body, 8)
    elif body.isascii() and body.isdigit():
        number = int(body)
    else:
        raise Fatal("bad numeric config value")
    return sign * number * factor


def check_repository_format(common):
    """setup.c check_repository_format_gently and verify_repository_format."""
    try:
        data = read_bytes(os.path.join(common, "config"))
    except OSError:
        return 40
    values = parse_config(data)
    version = 0
    if "core.repositoryformatversion" in values:
        version = config_int(values["core.repositoryformatversion"][-1])
    if version > 1:
        raise Fatal("repository format version too new")
    hex_length = 40
    for name, entries in values.items():
        if not name.startswith("extensions."):
            continue
        extension = name[len("extensions.") :]
        if extension in V0_EXTENSIONS:
            continue
        if extension in V1_ONLY_EXTENSIONS:
            if version == 0:
                raise Fatal("v1-only extension in a version 0 repository")
            if extension == "objectformat":
                algorithm = entries[-1]
                if algorithm == "sha256":
                    hex_length = 64
                elif algorithm != "sha1":
                    raise Fatal("unknown object format")
            continue
        if version >= 1:
            raise Fatal("unknown repository extension")
    return hex_length


# --- refs ----------------------------------------------------------------------


def refname_ok(name):
    """refs.c check_refname_format with REFNAME_ALLOW_ONELEVEL."""
    if not name or name == "@" or "@{" in name or ".." in name:
        return False
    if name.endswith("/") or name.endswith("."):
        return False
    for component in name.split("/"):
        if not component or component.startswith(".") or component.endswith(".lock"):
            return False
    for ch in name:
        if ord(ch) < 0x20 or ord(ch) == 0x7F or ch in " ~^:?*[\\":
            return False
    return True


def parse_oid(data, hex_length):
    """An object id followed by end of file or whitespace, else None."""
    oid = data[:hex_length]
    if len(oid) != hex_length or not is_hex(oid):
        return None
    rest = data[hex_length:]
    if rest and rest[:1] not in GIT_SPACE:
        return None
    return oid.decode("ascii").lower()


def read_packed_refs(common, hex_length):
    """packed-backend.c: {refname: oid}; malformed files are fatal."""
    try:
        data = read_bytes(os.path.join(common, "packed-refs"))
    except OSError:
        return {}
    refs = {}
    lines = data.split(b"\n")
    if lines[-1] != b"":
        raise Fatal("unterminated line in packed-refs")
    lines = lines[:-1]
    if lines and lines[0].startswith(b"#"):
        if not lines[0].startswith(b"# pack-refs with:"):
            raise Fatal("invalid line in packed-refs")
        lines = lines[1:]
    previous = None
    for line in lines:
        if line.startswith(b"^"):
            if previous is None or parse_oid(line[1:], hex_length) is None or len(line) != hex_length + 1:
                raise Fatal("invalid peel line in packed-refs")
            continue
        oid = line[:hex_length]
        if len(oid) != hex_length or not is_hex(oid) or line[hex_length : hex_length + 1] != b" ":
            raise Fatal("invalid line in packed-refs")
        name = os.fsdecode(line[hex_length + 1 :])
        refs[name] = oid.decode("ascii").lower()
        previous = name
    return refs


def read_loose(gitdir, common, name):
    """('sym', target), ('raw', contents), or None when the ref file is absent."""
    base = gitdir if not name.startswith("refs/") else common
    path = os.path.join(base, name)
    try:
        if os.path.islink(path):
            target = os.readlink(path)
            if target.startswith("refs/") and refname_ok(target):
                return ("sym", target)
        if not os.path.isfile(path):
            return None
        data = read_bytes(path)
    except OSError:
        return None
    return parse_ref_contents(data)


def parse_ref_contents(data):
    if data.startswith(b"ref:"):
        target = data[4:].strip(GIT_SPACE)
        return ("sym", os.fsdecode(target))
    return ("raw", data)


def resolve(gitdir, common, packed, name, hex_length):
    """refs.c refs_resolve_ref_unsafe(RESOLVE_REF_READING): oid or None."""
    for _ in range(SYMREF_MAXDEPTH + 1):
        loose = read_loose(gitdir, common, name)
        if loose is None:
            return packed.get(name)
        kind, value = loose
        if kind == "raw":
            oid = parse_oid(value, hex_length)
            return oid
        if not refname_ok(value):
            return None
        name = value
    return None


def walk_loose(common, prefix):
    """Loose ref names under prefix, skipping dot-files and *.lock like git."""
    names = []
    top = os.path.join(common, prefix)

    def visit(directory, relative, depth):
        # Like loose_fill_ref_dir, classify entries by following symlinks and
        # skip anything that is neither a directory nor a regular file.
        if depth > 40:
            return
        try:
            entries = sorted(os.listdir(directory))
        except OSError:
            return
        for entry in entries:
            if entry.startswith(".") or entry.endswith(".lock"):
                continue
            path = os.path.join(directory, entry)
            name = f"{relative}/{entry}"
            if os.path.isdir(path):
                visit(path, name, depth + 1)
            elif os.path.isfile(path):
                names.append(name)

    visit(top, prefix.rstrip("/"), 0)
    return names


def shorten(refname):
    for prefix in ("refs/heads/", "refs/remotes/", "refs/tags/", "refs/"):
        if refname.startswith(prefix):
            return refname[len(prefix) :]
    return refname


def branch_lines(gitdir, common, hex_length):
    packed = read_packed_refs(common, hex_length)
    names = set(walk_loose(common, "refs/heads/")) | set(walk_loose(common, "refs/remotes/"))
    names |= {n for n in packed if n.startswith("refs/heads/") or n.startswith("refs/remotes/")}
    head = read_loose(gitdir, common, "HEAD")
    current = head[1] if head and head[0] == "sym" else None
    lines = []
    if head and head[0] == "raw":
        oid = parse_oid(head[1], hex_length)
        if oid is not None:
            lines.append(f"* (HEAD detached at {oid[:7]})")
    locals_, remotes = [], []
    for name in sorted(names):
        if not refname_ok(name):
            continue
        loose = read_loose(gitdir, common, name)
        oid = resolve(gitdir, common, packed, name, hex_length)
        # A loose ref that resolves to the null id is broken; a packed one is not.
        if oid is None or (loose is not None and oid == "0" * hex_length):
            continue
        display = shorten(name) if name.startswith("refs/heads/") else "remotes/" + shorten(name)
        if loose is not None and loose[0] == "sym":
            display += " -> " + shorten(loose[1])
        marker = "* " if name == current else "  "
        (locals_ if name.startswith("refs/heads/") else remotes).append(marker + display)
    return lines + locals_ + remotes


def git_branch_all():
    """(exit status, output lines) of `git branch -a` run in /app/repo."""
    if not os.path.isdir(REPO):
        return -1, []
    try:
        gitdir = discover(REPO)
        common = common_dir(gitdir)
        hex_length = check_repository_format(common)
        lines = branch_lines(gitdir, common, hex_length)
    except (Fatal, OSError, RecursionError):
        return 128, []
    return 0, lines[:MAX_LINES]


def main():
    sys.stdin.buffer.read()
    status, lines = git_branch_all()
    observation = {
        "git_path_exists": os.path.exists(os.path.join(REPO, ".git")),
        "branch_exit_status": status,
        "branch_output_lines": [
            line.encode("utf-8", "replace").decode("utf-8")[:1024] for line in lines
        ],
    }
    sys.stdout.write(json.dumps({"observation": observation}))


if __name__ == "__main__":
    main()
