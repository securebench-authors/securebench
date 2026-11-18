# feal-linear-cryptanalysis (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/feal-linear-cryptanalysis/task`, `sha256:b816e3805590d29369fc8dcdf3e7c83dc2d1d6d4d773b8c2856287b3ede76ad6`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:dbd3f32581fd661e9b2b8b80d6ba9b1808f4f79ef164d696c09a772857c70705`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:6809fb8e9ce45bcf41e85e4e658c2b10ccc31603b2abc76d7ff236d31efea642`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/derive.py`, `hidden/expected.json`.
- The source pack has no `evaluation/`, so `/grader/evaluation/` is an empty folder.
