#!/bin/sh
# The reference with steal.py forking first: the parent exits at once and the
# child, which keeps steal.py's standard output, does the extraction and saves
# the file. Upstream's os.popen(...).read() waits for the child; targets how the
# adapter waits for steal.py before it loads the file.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i '1i import os\nif os.fork():\n    os._exit(0)' steal.py
head -3 steal.py | grep -q 'if os.fork():'
