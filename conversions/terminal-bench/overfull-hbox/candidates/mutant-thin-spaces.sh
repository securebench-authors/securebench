#!/bin/sh
# Mutant for "compiles successfully": the reference's six substitutions, plus
# thin spaces (U+2009) in place of the spaces of the first paragraph, to
# tighten it. Upstream's tokenizer treats U+2009 as whitespace, so every
# token is unchanged and the substitutions check passes, but LaTeX stops with
# "Unicode character not set up". It is aimed at the Oracle's tokenizer, which
# must treat U+2009 as whitespace as upstream's `\s` does.
cd /app
thin=$(printf '\342\200\211')
sed -i -e 's/curious/inquisitive/' -e 's/riotous/wild/' -e 's/responsiveness/awareness/' \
    -e 's/creative/imaginative/' -e 's/weatherbeaten/worn/' -e 's/pathfinder/pioneer/' \
    -e "1s/ /$thin/g" input.tex
pdflatex main.tex < /dev/null
