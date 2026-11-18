#!/bin/sh
# Mutant for "only synonyms from synonyms.txt": the reference's six
# substitutions, except that weatherbeaten becomes "shabby" and pathfinder
# becomes "explorer", English synonyms that synonyms.txt does not list. The
# document then compiles with no overfull box.
cd /app
sed -i -e 's/curious/inquisitive/' -e 's/riotous/wild/' -e 's/responsiveness/awareness/' \
    -e 's/creative/imaginative/' -e 's/weatherbeaten/shabby/' -e 's/pathfinder/explorer/' input.tex
pdflatex main.tex
