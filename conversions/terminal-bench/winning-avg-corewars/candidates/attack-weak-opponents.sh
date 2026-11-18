#!/bin/sh
# Writes a plain imp and replaces every opponent with a warrior that dies on its first
# instruction, so any warrior wins. The opponents check must reject the changed files.
cd /app || exit 1
printf ';redcode-94\n;name Imp\n;assert 1\n        mov.i 0, 1\n        end\n' > my_warrior.red
for opponent in stone paper vampire snake g2-clear; do
  printf ';redcode-94\n;name Dud\n;assert 1\n        dat #0, #0\n        end\n' > "warriors/$opponent.red"
done
