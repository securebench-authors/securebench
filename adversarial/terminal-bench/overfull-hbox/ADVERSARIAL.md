# overfull-hbox (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/overfull-hbox/task`, `sha256:b125925bac2e1c18e26160dc7e2c3b4ec16ea642a029c30820dc86cca265501c`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:376e1a8d6e8b8785f7d8650765a71df062e2cb5fc2919b3b17ca7ff3263063ad`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:f9fe9335d55e5713f260975be759311aa5e505fe0d69a6e756c62f4be2018df9`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/input.tex`, `hidden/log.json`, `hidden/main.tex`, `hidden/synonyms.txt`.
