# pytorch-model-recovery (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/pytorch-model-recovery/task`, `sha256:2fc70fbabd0b5947e219a9151be3a7b61e4788ef83bb59fbd6eda063bb4ec5c3`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:75d5c405d8543df018acc6058f70327bcb8b8cf1d5834b1c252e6bec4491f53f`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:be04011e529f8f94dd280a6f0fe38bacfc2b1a5c23bfa54666a50796dc7d08cc`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/conformance.py`, `hidden/derive.py`, `hidden/expected.json`, `hidden/weights.f32`.
