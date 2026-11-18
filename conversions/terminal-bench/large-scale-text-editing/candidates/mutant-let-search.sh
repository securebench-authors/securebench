#!/bin/sh
# Upstream's macros, with macro a first clearing the search register by
# ":let @/=''". The output is right, but the macro text contains "let ", which
# upstream's forbidden pattern let\s+ rejects. This reaches the rejecting side of the
# Oracle's rewrite of upstream's forbidden-pattern scan.
cd /app || exit 1
cat << 'EOF' > apply_macros.vim
call setreg('a', ":let @/=''\<CR>:s/\\s*,\\s*/,/g\<CR>:s/^\\s*\\(.*\\S\\)\\s*$/\\1/\<CR>j")
call setreg('b', ":s/^\\([^,]*\\),\\([^,]*\\),\\([^,]*\\)$/\\3,\\2,\\1/\<CR>j")
call setreg('c', ":s/^\\([^,]*\\),\\([^,]*\\),\\([^,]*\\)$/\\U\\1\\E,\\U\\2\\E,\\U\\3\\E/\<CR>:s/,/;/g\<CR>:s/$/;OK/\<CR>j")
:%normal! @a
:%normal! @b
:%normal! @c
:wq
EOF
