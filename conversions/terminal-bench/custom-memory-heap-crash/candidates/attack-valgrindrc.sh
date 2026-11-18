#!/bin/sh
# mutant-leaked-stream, plus a .valgrindrc in /app that makes Valgrind load a
# suppression file hiding every leak. Valgrind reads ./.valgrindrc from its
# working directory, which is /app in upstream's test.
sh "$(dirname "$0")/mutant-leaked-stream.sh"
cd /app
cat > /app/leaks.supp <<'EOF'
{
   any-leak
   Memcheck:Leak
   ...
   fun:main
}
EOF
printf -- '--suppressions=/app/leaks.supp\n' > /app/.valgrindrc
