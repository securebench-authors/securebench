# One of the two compile commands of upstream's test_outputs.py, chosen by the
# protocol check ($1 is rust or cpp), run once on the replayed candidate.
# Upstream ignores whether they succeed (os.popen), so a failed build leaves
# the binary missing and the cases fail; setup itself always succeeds.
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH
cd /app || exit 0
case "$1" in
  rust) rustc /app/polyglot/main.rs -o /app/polyglot/main >&2 ;;
  cpp) g++ -x c++ /app/polyglot/main.rs -o /app/polyglot/cmain >&2 ;;
  *) exit 1 ;;
esac
exit 0
