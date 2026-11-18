#!/bin/sh
# Mutant for "no overfull hbox": replaces every word that synonyms.txt lists
# with the shortest member of its family, without compiling to check. Every
# change is an allowed substitution, but one overfull box remains.
cd /app
awk -F', ' '
NR == FNR {
    best = $1
    for (i = 2; i <= NF; i++) if (length($i) < length(best)) best = $i
    for (i = 1; i <= NF; i++) shortest[$i] = best
    next
}
{
    out = ""
    line = $0
    while (match(line, /[A-Za-z]+/)) {
        word = substr(line, RSTART, RLENGTH)
        if (word in shortest) word = shortest[word]
        out = out substr(line, 1, RSTART - 1) word
        line = substr(line, RSTART + RLENGTH)
    }
    print out line
}' synonyms.txt input.tex > input.tex.new
mv input.tex.new input.tex
pdflatex main.tex
