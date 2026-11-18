# rstan-to-pystan (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/rstan-to-pystan/task`, `sha256:fd287e7c97285160f43bbe2b4d3bb433caf47a3e9a0e6da9b9cceeeff6c4eef8`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:855b6ea47411fe46bf4d065abd9f2e21bb942ae5c60ca8398a2330413925903e`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:b4d3e38bf01f4cd9048ee01ac98dfd38974c699b68ceda31d027cba19347019e`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/differential.py`, `hidden/ranges.json`.
- The source pack has no `evaluation/`, so `/grader/evaluation/` is an empty folder.
