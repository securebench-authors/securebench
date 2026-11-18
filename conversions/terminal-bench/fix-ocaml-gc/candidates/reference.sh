#!/bin/sh
# Upstream solution/solve.sh, unchanged apart from the explicit cd.
cd /app || exit 1

echo Running solution

sed -i '650s/Whsize_hd(hd)/wh/' /app/ocaml/runtime/shared_heap.c
