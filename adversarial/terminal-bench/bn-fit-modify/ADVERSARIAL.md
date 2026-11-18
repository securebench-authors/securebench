# bn-fit-modify (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/bn-fit-modify/task`, `sha256:da06349a51a46f2a5b0beaff218dfbf90e4b712290ca14c6827df0c3b0756e3b`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:4c115d2c77a2ab9dc458cde52c2a179e55ebf9bce808a993d55e9ad0cb8dca62`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:a2960773a2cf3cb01b8d75cbc677da9df3b39eabb5af7ad228d314aa1a72c4b5`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/derive_expected.py`, `hidden/differential.py`, `hidden/expected.json`.
- The source pack has no `evaluation/`, so `/grader/evaluation/` is an empty folder.
