#!/bin/sh
# Upstream's macros padded to 199 keystrokes, the most upstream allows, counting the
# special keys <Esc> and <CR> as one keystroke each. It also uses the other forms
# upstream accepts: ":call", double-quoted register names, indented and comment
# lines, and ":x". Both graders should pass it.
cd /app || exit 1
cat << 'EOF' > apply_macros.vim
" Macro a trims the fields.
  :call setreg("a", ":s/\\s*,\\s*/,/g\<CR>:s/^\\s*\\(.*\\S\\)\\s*$/\\1/\<CR>j")
" Macro b reverses them.
call setreg('b', "\<Esc>:s/^\\([^,]*\\),\\([^,]*\\),\\([^,]*\\)$/\\3,\\2,\\1/\<CR>j")
call setreg("c", ":s/^\\([^,]*\\),\\([^,]*\\),\\([^,]*\\)$/\\U\\1\\E,\\U\\2\\E,\\U\\3\\E/\<CR>:s/,/;/g\<CR>:s/$/;OK/\<CR>00000000000000000000000000000000000j")

:%normal! @a
   :%normal! @b
:%normal! @c
:x
EOF
