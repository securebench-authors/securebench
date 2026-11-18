# password-recovery (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/password-recovery/task`, `sha256:3bb9eddffa9fe350b1e277bf9c4c57f7748ebffb0c877d152264267287de26c5`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:b8828be80f429d9245f9cf2802d7e0368d218facfa8d9fa04d99fc0c74d24130`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:c9ebd63054ce3f9a06787c0193ccd275ff7f8af93fe78d4d756928b5b720580c`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/expected.json`.
- The source pack has no `evaluation/`, so `/grader/evaluation/` is an empty folder.
