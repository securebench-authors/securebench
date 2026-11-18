#!/bin/sh
# Mutant for the newline translation: the reference's six substitutions, and
# main.tex, synonyms.txt and input.tex rewritten with CRLF line ends, as an
# editor set to Windows line ends would save them. Upstream reads all three in
# text mode, where CRLF becomes LF, so the files still count as unmodified and
# the tokens are unchanged; the Oracle translates newlines to match.
cd /app
sed -i -e 's/curious/inquisitive/' -e 's/riotous/wild/' -e 's/responsiveness/awareness/' \
    -e 's/creative/imaginative/' -e 's/weatherbeaten/worn/' -e 's/pathfinder/pioneer/' input.tex
sed -i -e 's/$/\r/' main.tex synonyms.txt input.tex
pdflatex main.tex
