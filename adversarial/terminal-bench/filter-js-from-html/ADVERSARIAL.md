# filter-js-from-html (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/filter-js-from-html/task`, `sha256:151548f990d7f3caf32cf6d17f583aaa68b5e21d292c1aef4e5b2dea219a53fa`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:42ed2742abe60cfa032761111dda1d5980ad7055d431f63c66e282f2b33f7e89`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:d54804176f3782edc6734072ae97df0a0f4a3fc033610fc356f1c9489d3cd76b`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/clean.json`, `hidden/derive.py`, `hidden/differential.py`, `hidden/vectors.json`.
