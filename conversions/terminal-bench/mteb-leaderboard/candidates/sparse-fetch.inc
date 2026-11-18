# Sourced by the mutants, from /app; not a candidate.
#
# The reference clones the whole results repository (2.6 GB checked out) and
# mteb then clones it a second time into ~/.cache/mteb/results. Qualification
# runs four candidates at once on a shared Docker data root, and SecureBench
# also snapshots each Agent container, so the mutants fetch only what the
# reference's leaderboard.py reads at the same commit: every model's
# model_meta.json and its result file for each task of MTEB(Scandinavian, v1)
# (6,653 files, 87 MB, byte-identical to the full clone's). mteb's cache entry
# points at this tree, so mteb reads it instead of cloning it.
set -e
commit=c0fd3271442f8c0c839084a109fede85c8514dab
tasks=$(python -c 'import mteb; print(" ".join(t.metadata.name for t in mteb.get_benchmark("MTEB(Scandinavian, v1)").tasks))')
git init -q /app/results
git -C /app/results remote add origin https://github.com/embeddings-benchmark/results
git -C /app/results fetch -q --depth 1 --filter=blob:none origin "$commit"
patterns="/results/*/*/model_meta.json"
for task in $tasks; do patterns="$patterns /results/*/*/$task.json"; done
git -C /app/results sparse-checkout set --no-cone $patterns
git -C /app/results checkout -q FETCH_HEAD
mkdir -p "$HOME/.cache/mteb"
ln -s /app/results "$HOME/.cache/mteb/results"
set +e
