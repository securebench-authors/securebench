#!/bin/sh
# Updates the files correctly but prints its confirmation in Latin-1, as code
# written for a legacy terminal might. Aimed at the adapter's UTF-8 record of
# standard output, which replaces upstream's capture_output=True, text=True:
# a decode error there fails the test.
cd /app || exit 1
# The reference program.py, taken from the heredoc in reference.sh.
awk '/^EOF$/{f=0} f; /^cat > program.py << .EOF.$/{f=1}' "$(dirname "$0")/reference.sh" > program.py || exit 1
printf '%s\n' '    sys.stdout.flush()' '    sys.stdout.buffer.write("Transaction processed £\n".encode("latin-1"))' >> program.py
tail -3 program.py
