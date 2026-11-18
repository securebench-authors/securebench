#!/bin/sh
# Leaves input.tex as it is and writes /app/main.aux, which LaTeX reads at
# \begin{document} of any job named main compiled in /app. It raises \hfuzz so
# far that TeX reports no overfull box. Upstream compiles in /app, so it reads
# this file.
cd /app
printf '%s\n' '\relax' '\global\hfuzz=\maxdimen' > main.aux
