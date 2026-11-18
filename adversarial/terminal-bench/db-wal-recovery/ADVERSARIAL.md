# db-wal-recovery (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/db-wal-recovery/task`, `sha256:a35b76b46942afbea1d33877feee5c43a54356586eac12c941bb74a567690795`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:35dd44f2b404c739ba7712bb52fb12376f3bd081e2e26c7efd55863eab20055d`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:e4af3eb051a71b3c8e0bcf348f038132fb47fadc6ac46a0ed2cb26af65f8173c`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/expected.json`.
- The source pack has no `evaluation/`, so `/grader/evaluation/` is an empty folder.
