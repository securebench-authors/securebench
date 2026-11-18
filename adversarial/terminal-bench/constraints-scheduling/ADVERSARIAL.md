# constraints-scheduling (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/constraints-scheduling/task`, `sha256:74ebb9ca414a8958e16d9d86dc332618e39c944490d895edfc63b90cb5232d10`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:bb440f78b3aa42e4dc60549a15e3a11bb5137cbc461f665a63f22a1a487bf2cd`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:f8230dadad3aba777860b5257b498e508aed9e0ed8eec72f4e9acd03865acb34`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/calendars.json`, `hidden/derive.py`, `hidden/spec.json`.
- The source pack has no `evaluation/`, so `/grader/evaluation/` is an empty folder.
