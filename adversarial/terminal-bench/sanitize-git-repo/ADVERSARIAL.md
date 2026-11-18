# sanitize-git-repo (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/sanitize-git-repo/task`, `sha256:8b88e9ae92b851aee8545ebe3a44331025dcc4b65387cc6987dc361a2a4bea42`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:b6197004f1c169cbbd73324fbdb984cebec50becec7e45775d7ccd7aa57c093d`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:fd211e303feb006b1f4f47a3d6def8a304d900fa4595ad1c23fb79067af83cb6`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive_manifest.py`, `hidden/expected/process.py`, `hidden/expected/ray_cluster.yaml`, `hidden/expected/rw_v2_fasttext_openhermes_vs_rw_v2_bigram_0.1_arcade100k.json`, `hidden/manifest.json`.
