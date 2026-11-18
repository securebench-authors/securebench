# path-tracing-reverse (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/path-tracing-reverse/task`, `sha256:9e64f3fe6a263714dcaa6a13ae09767c4185e4b1235f2050eca89274d7d03c35`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:67f163bb975fa936aa8f1fba52c1840bf66fd39bff443eaec151b7801e7cff17`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:c0b78ce08f0dcc0e8c8b76cd927deb12d645dce0d213ccae82beaa816415538a`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/derive.py`, `hidden/differential.py`, `hidden/expected.json`, `hidden/original-rgb.zlib`.
