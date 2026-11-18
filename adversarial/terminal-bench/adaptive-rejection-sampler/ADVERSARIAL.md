# adaptive-rejection-sampler (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/adaptive-rejection-sampler/task`, `sha256:030459e0ab7b158cd08e3449031ccb155d9cf83f7b88e905d55525798ae16007`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:227d5c0808fceeb596f115d7ed6a6d0455ffaa7be21e2cb1893db4649a51e7fd`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:d50116c97f7c57b79db57297147961a0b73bcc893244faf1abef6df650098cb4`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive-r.sh`, `hidden/r-packages.txt`, `hidden/tests/generate.R`, `hidden/tests/logconcave.R`, `hidden/tests/validation.R`.
