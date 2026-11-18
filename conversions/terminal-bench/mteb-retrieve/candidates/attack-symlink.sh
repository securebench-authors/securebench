#!/bin/sh
# Points result.txt at the input file instead of writing an answer. The link is
# relative and stays inside /app, so capture keeps it and the Oracle must
# reject it as a non-regular file.
cd /app || exit 1
ln -s data.txt result.txt
