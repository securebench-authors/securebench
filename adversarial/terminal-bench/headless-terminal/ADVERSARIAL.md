# headless-terminal (adversarial copies)

Adversarial copies for the adversarial campaign. They are not conversions: they are never qualified, reviewed as conversions or counted. `adversarial/campaign.py build` makes them; they are not committed, and rebuilding from the commit they were built at gives the digests below.

- Source pack: `conversions/terminal-bench/headless-terminal/task`, `sha256:962b22803b89befe3c9c27cb13e507d7934ef5af1c2097a54a58a4a3164c9e4a`, the digest its qualification records.
- Architecture copy: `docs/architecture.md`, `sha256:4347fc4a7d1d5bf82b64f003e774d985253ec6a28f945ff591c148f9293fa84c`, mounted read-only at `/securebench` in both copies.
- `task/`: black box, `sha256:5d9f2b6416e004aedc2a0085efa22020315e64d58ebb6008a154f1f648434e63`. It differs from the source in `instructions.md` (the text of `adversarial/brief-black-box.md` appended after the task), `public/securebench/` and one `[[public_assets]]` entry in `task.toml`.
- `task-white-box/`: white box, `sha256:7efd2f26c265be6cede23beb680fc87e963fae078f1dc11d6d36eee987c5955b`. Its brief is `adversarial/brief-white-box.md`, and it also has `public/grader/evaluation/`, an exact copy of `evaluation/`, and `public/grader/hidden/oracle.py`, mounted read-only at `/grader` by a second `[[public_assets]]` entry.
- Hidden files the white box leaves out: `hidden/cases.json`, `hidden/tests/test_background_commands.py`, `hidden/tests/test_cancel_command.py`, `hidden/tests/test_import.py`, `hidden/tests/test_send_interactive_command.py`, `hidden/tests/test_send_non_interactive_command.py`, `hidden/tests/test_shell_state_persists_between_commands.py`, `hidden/tests/test_startup_files.py`.
