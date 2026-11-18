#!/bin/sh
# The reference, but pyknotid itself is not left installed in the global
# environment: the extensions are built in place and the dependencies are
# installed, so it works only when run from /app/pyknotid.
sh "$(dirname "$0")/reference.sh"
cd /app
pip uninstall -y pyknotid
