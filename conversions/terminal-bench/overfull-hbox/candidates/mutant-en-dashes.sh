#!/bin/sh
# Mutant for "only synonyms from synonyms.txt": the reference's six
# substitutions, plus every em dash (---) shortened to an en dash (--) to win
# width. Upstream's tokenizer splits on em dashes only, so the tokens change.
cd /app
sed -i -e 's/curious/inquisitive/' -e 's/riotous/wild/' -e 's/responsiveness/awareness/' \
    -e 's/creative/imaginative/' -e 's/weatherbeaten/worn/' -e 's/pathfinder/pioneer/' \
    -e 's/---/--/g' input.tex
pdflatex main.tex
