# fix-git (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/fix-git/task`, `sha256:84e478d5ab03da564e830d70586e9490be574c389c16bb914f2bee867bb4f4e1`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:c42748ee85b91bca4d39db644a45c8f7d7ad354a24e8d70eba2dde80c91ee5bb`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:b250e19e5fe9142b3b27547cce9dd9577bf8484aa9e7816ff1c569af570e0f1c`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/about.md`, `hidden/default.html`, `hidden/differential.py`.
- The source pack has no `evaluation/`, so `/grader/evaluation/` is an empty folder.
