#!/bin/sh
# Upstream's macros with 37 no-op "0" motions added to macro c: the output is right,
# but the macros take exactly 200 keystrokes, one more than upstream's "< 200" allows.
cd /app || exit 1
cat << 'EOF' > apply_macros.vim
call setreg('a', ":s/\\s*,\\s*/,/g\<CR>:s/^\\s*\\(.*\\S\\)\\s*$/\\1/\<CR>j")
call setreg('b', ":s/^\\([^,]*\\),\\([^,]*\\),\\([^,]*\\)$/\\3,\\2,\\1/\<CR>j")
call setreg('c', ":s/^\\([^,]*\\),\\([^,]*\\),\\([^,]*\\)$/\\U\\1\\E,\\U\\2\\E,\\U\\3\\E/\<CR>:s/,/;/g\<CR>:s/$/;OK/\<CR>0000000000000000000000000000000000000j")
:%normal! @a
:%normal! @b
:%normal! @c
:wq
EOF
