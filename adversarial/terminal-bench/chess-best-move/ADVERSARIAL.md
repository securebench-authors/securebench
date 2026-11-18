# chess-best-move (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/chess-best-move/task`, `sha256:9502a8b195d6c453b843ebd390b0974f46fdac7c95688b72a9afeda4b171b297`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:43001a9dda4c95a2beef19f8e2a167f48272049b31aaa377168f13fd1418c17e`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:a8c2c5f1816a60274fa93ea2c6846dbc6b352472e0cb271026958f0da4b17414`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/differential.py`, `hidden/expected.json`.
- The source pack has no `evaluation/`, so `/grader/evaluation/` is an empty folder.
