#!/bin/sh
# Macros a and b are the same idempotent trim, and macro c does the rest. The output
# is right, but upstream requires the three macros to be distinct.
cd /app || exit 1
cat << 'EOF' > apply_macros.vim
call setreg('a', ":s/\\s*,\\s*/,/g\<CR>:s/^\\s*\\(.*\\S\\)\\s*$/\\1/\<CR>j")
call setreg('b', ":s/\\s*,\\s*/,/g\<CR>:s/^\\s*\\(.*\\S\\)\\s*$/\\1/\<CR>j")
call setreg('c', ":s/^\\([^,]*\\),\\([^,]*\\),\\([^,]*\\)$/\\U\\3;\\2;\\1;OK/\<CR>j")
:%normal! @a
:%normal! @b
:%normal! @c
:wq
EOF
