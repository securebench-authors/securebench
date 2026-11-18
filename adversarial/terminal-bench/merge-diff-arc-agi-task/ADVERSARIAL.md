# merge-diff-arc-agi-task (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/merge-diff-arc-agi-task/task`, `sha256:332d80e338f05eee33bc22f3e56a803979678e1c0d540501a5454306aa6823c5`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:39387842c82a7b539e1ab649cf95d23c56874c55f5b0f5615de5075ed5d2b5bc`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:3e03a284ae2c80908d7daef0d670bfcab17f3151036c4510a193d2fe0ff890cc`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/git-differential/compare.py`, `hidden/git-differential/scenarios.sh`, `hidden/repository.json`, `hidden/test.json`.
