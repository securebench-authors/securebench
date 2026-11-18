#!/bin/sh
# Upstream's macros with a trailing comment on each setreg line, written with CRLF
# line ends. Upstream's test reads the script with universal newlines and strips
# each line, so the CRLF ends alone would pass its line checks, but it requires each
# setreg line to end with the closing quote and parenthesis, which the comments
# break. Vim also exits non-zero on the CRLF script. This exercises the Oracle's
# newline translation on a script that reaches its line checks.
cd /app || exit 1
cat << 'EOF' | awk '{ printf "%s\r\n", $0 }' > apply_macros.vim
call setreg('a', ":s/\\s*,\\s*/,/g\<CR>:s/^\\s*\\(.*\\S\\)\\s*$/\\1/\<CR>j") " trim
call setreg('b', ":s/^\\([^,]*\\),\\([^,]*\\),\\([^,]*\\)$/\\3,\\2,\\1/\<CR>j") " reverse
call setreg('c', ":s/^\\([^,]*\\),\\([^,]*\\),\\([^,]*\\)$/\\U\\1\\E,\\U\\2\\E,\\U\\3\\E/\<CR>:s/,/;/g\<CR>:s/$/;OK/\<CR>j") " upper
:%normal! @a
:%normal! @b
:%normal! @c
:wq
EOF
