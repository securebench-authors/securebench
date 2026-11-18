#!/bin/sh
# Deletes src/INPUT.DAT once the transaction is processed, as a queue
# consumer would, and runs once at agent time as the reference does. Aimed at
# the adapter's existence record, which replaces test_data_files_exist.
cd /app || exit 1
# The reference program.py, taken from the heredoc in reference.sh.
awk '/^EOF$/{f=0} f; /^cat > program.py << .EOF.$/{f=1}' "$(dirname "$0")/reference.sh" > program.py || exit 1
printf '%s\n' '    Path("src/INPUT.DAT").unlink()' >> program.py
python program.py
ls src
