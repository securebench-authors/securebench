"""The candidate (architecture Section 5): baseline index, capture, store, replay and lookup.

Public interface:

- `store.Store`: the content-addressed candidate store.
- `state.BaselineIndex`, `state.compute_delta`, `state.FinalView`: pure delta semantics.
- `index.build_index`, `index.check_repository`: the live baseline checks.
- `capture.capture`: the candidate from a stopped Agent snapshot.
- `capture.collect`: Output Artifacts from a stopped Evaluation snapshot.
- `replay.replay`: the replayed candidate image.
- `lookup.read_file`, `lookup.list_directory`: artifact-check reads without an environment.
"""
