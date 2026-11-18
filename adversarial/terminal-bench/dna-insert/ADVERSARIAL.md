# dna-insert (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/dna-insert/task`, `sha256:27d8dc2a9be2d87b8df37acca406b4af12400dda9f055293ba5823fb63855b9d`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:e6b59105002442d5f492e2400bb4377d8f489e96bd54668941e2af47ef63d85c`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:44f042a654a325dbd699afa66fc86144a87182faae520427070619752f1f970b`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/derive_oligotm.py`, `hidden/differential.py`, `hidden/expected.json`, `hidden/oligotm.json`.
- The source pack has no `evaluation/`, so `/grader/evaluation/` is an empty folder.
