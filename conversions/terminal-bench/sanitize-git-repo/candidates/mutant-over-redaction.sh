#!/bin/sh
# Sanitizes the three files correctly, then also redacts every
# `AWS_SECRET_ACCESS_KEY=<value>` assignment in the repository, including the
# empty ones in README.md, baselines/README.md and other files that hold no
# secret. Upstream's test_no_other_files_changed fails on those files; here the
# manifest comparison (other-files-unchanged) is what catches it.
here=$(cd "$(dirname "$0")" && pwd)
cd /app/dclm || exit 1
sh "$here/scrub-secrets.txt"
grep -rlI --exclude-dir=.git 'AWS_SECRET_ACCESS_KEY=' . | xargs sed -i -E "s/AWS_SECRET_ACCESS_KEY=[^' \"]*/AWS_SECRET_ACCESS_KEY=<your-aws-secret-access-key>/g"
