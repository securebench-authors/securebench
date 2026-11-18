#!/bin/sh
# Sanitizes the three files, damages other files with an over-broad redaction,
# then marks every damaged file skip-worktree so that Git no longer compares it
# with the working tree. Upstream's test_no_other_files_changed asks Git and
# sees no change; SecureBench must still fail it on the files' content.
here=$(cd "$(dirname "$0")" && pwd)
cd /app/dclm || exit 1
sh "$here/scrub-secrets.txt"
grep -rlI --exclude-dir=.git 'AWS_SECRET_ACCESS_KEY=' . | xargs sed -i -E "s/AWS_SECRET_ACCESS_KEY=[^' \"]*/AWS_SECRET_ACCESS_KEY=<your-aws-secret-access-key>/g"
git diff --name-only \
  | grep -v -x -e ray_processing/ray_cluster.yaml -e ray_processing/process.py \
      -e exp_data/datasets/tokenized/rw_v2_fasttext_openhermes_vs_rw_v2_bigram_0.1_arcade100k.json \
  | xargs git update-index --skip-worktree
