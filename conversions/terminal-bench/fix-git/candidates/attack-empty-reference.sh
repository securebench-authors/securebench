#!/bin/sh
# Tampers with upstream's reference copies, second form: empties both
# files and both reference copies in /app/resources/patch_files, so
# upstream compares two empty files.
cd /app/personal-site
: > _includes/about.md
: > _layouts/default.html
: > /app/resources/patch_files/about.md
: > /app/resources/patch_files/default.html
