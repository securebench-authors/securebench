# dna-assembly (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/dna-assembly/task`, `sha256:c03be1edad523395c39cee34d4ec741561c9140a322a0818583754bba5a2823b`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:7ad6058ea4b20ada1d936002e76301c99adb33139626885c973827507398ffc6`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:e8d775a392f41c9abcfb5eb88579c21c3d45f1272c89e67cce51333a07289699`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/check_oligotm.py`, `hidden/templates.json`.
- The source pack has no `evaluation/`, so `/grader/evaluation/` is an empty folder.
