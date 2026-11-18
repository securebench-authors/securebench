#!/bin/sh
# Writes the data files as UTF-8 with a byte-order mark, as tools that target
# Windows consumers do. Aimed at decoding: upstream's read_text() keeps the
# mark as U+FEFF, while SecureBench's text parser rejects the file outright.
cd /app || exit 1
# The reference program.py, taken from the heredoc in reference.sh.
awk '/^EOF$/{f=0} f; /^cat > program.py << .EOF.$/{f=1}' "$(dirname "$0")/reference.sh" > program.py || exit 1
sed -i 's/^    with open("data\/\([A-Z]*\).DAT", "w") as f:$/    with open("data\/\1.DAT", "w", encoding="utf-8-sig") as f:/' program.py
grep -c 'utf-8-sig' program.py
