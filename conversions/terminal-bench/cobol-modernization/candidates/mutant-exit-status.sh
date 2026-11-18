#!/bin/sh
# Updates the files correctly but exits with status 1, the number of
# transactions it handled, as batch jobs that report a count do. Aimed at
# the adapter's record of exit statuses, which replaces upstream's returncode
# assertions.
cd /app || exit 1
# The reference program.py, taken from the heredoc in reference.sh.
awk '/^EOF$/{f=0} f; /^cat > program.py << .EOF.$/{f=1}' "$(dirname "$0")/reference.sh" > program.py || exit 1
printf '%s\n' '    sys.exit(1)' >> program.py
tail -3 program.py
