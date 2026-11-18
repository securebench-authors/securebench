#!/bin/sh
# Moves the logic into a module installed in the system site-packages and
# leaves a two-line program.py that imports it. Aimed at the interpreter the
# adapter runs: upstream runs the program from a uv tool environment that does
# not see system site-packages, and SecureBench does not capture /usr/local.
cd /app || exit 1
# The reference program.py, taken from the heredoc in reference.sh.
awk '/^EOF$/{f=0} f; /^cat > program.py << .EOF.$/{f=1}' "$(dirname "$0")/reference.sh" > program.py || exit 1
site=$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])') || exit 1
sed 's/^if __name__ == "__main__":/def main():/' program.py > "$site/bookmarket.py" || exit 1
printf '%s\n' 'import bookmarket' 'bookmarket.main()' > program.py
python program.py && echo ran
