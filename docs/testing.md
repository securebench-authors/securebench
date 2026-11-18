# Testing

How SecureBench is tested: where the tests live, the fixture tasks that serve as end-to-end tests, and which tests demonstrate each security property.

## 1. Test layout

```
tests/unit/          fast tests, no Docker
tests/adversarial/   attack cases against trusted code, unit-level where possible
tests/integration/   need Docker; include the B1 to B8 qualification suite
tests/fixtures/      end-to-end runs of the fixture tasks (need Docker)
```

Everything under `tests/integration/` and `tests/fixtures/` carries the `integration` marker.

## 2. Fixture tasks

Fixture tasks are small, cheap tasks that exercise the whole pipeline. They are the end-to-end tests of the framework. They need no paid model. Each candidate is produced by a scripted harness (a fixed command sequence), so runs are fast and deterministic.

Each lives in `fixtures/<name>/`: the task pack in `task/` (format of `docs/task-format.md`) and the scripted candidates in `candidates/`, one shell script each, run by the scripted harness in the Agent environment. F1, F3 and F5 use the stock `python:3.12-slim` baseline with scope roots under `/srv`; F2 builds its baseline from a Dockerfile under `fixtures/`.

Every fixture task comes with at least three candidates:

- **correct:** must pass;
- **wrong:** a plausible but incorrect solution, must fail with class `oracle`;
- **malicious:** attacks the pipeline and must fail with the expected class or be rejected. An attack on capture or on the network must have no effect instead: excluded edits never enter the candidate, and forbidden routes fail and are logged. Such a candidate may then pass on its honest work.

### F1. Answer file (passive check only)

The agent writes `/srv/answer.json` containing the answer to a question in the instructions.

- Exercises: capture with a small scope, the candidate store, lookup, the strict JSON parser, the Oracle, result records.
- Correct: the right answer. Wrong: a different answer.
- Malicious, each a separate candidate:
  - `/srv/answer.json` is a symlink to a file outside the scope;
  - a file larger than the scope's bound;
  - a named pipe or device file inside the scope;
  - JSON with duplicate keys or non-finite numbers.

### F2. Small repository with a build (active check with shared setup)

A tiny repository (a few files in a compiled language, such as C) at a pinned commit. The task asks for a sorting option. The shared setup builds the program once; each case runs it on inputs from the challenge.

- Exercises: repository baseline with commit check, `**/.git` exclusion, scope excludes for tests, shared setup snapshot and cloning, several cases in parallel, cancellation after the first failure, typed observations.
- Correct: the reference change. Wrong: a mutant that sorts in the wrong order. Build failure: a change that does not compile, which must fail with class `setup`.
- Malicious, each a separate candidate:
  - edits excluded test files, which must not appear in the candidate;
  - hardcodes the output of the public example;
  - tries to read hidden resources or write to the adapter's mount point;
  - plants Git hooks or Git configuration in the repository.

### F3. Generated file (output files)

The candidate is a program that, given the challenge, writes a JSON file. The file is collected from the stopped Evaluation environment and parsed with the strict JSON parser.

- Exercises: output file collection in a utility environment, registry parsing, binding.
- Correct, wrong, and malicious: the output path is a symlink to an evaluation input, or the file exceeds its bound.

### F4. Allowed domain (Agent network policy)

The task requires downloading a file from one allowed domain during the Agent phase. In tests, the domain is served by a controlled server on the test network described below; the proxy has no test-only code path.

- Exercises: the per-run restricted network, the egress proxy, the provider relay path (with a stub provider), proxy and relay logs.
- The scripted harness also tries forbidden actions, each of which must fail and appear in the proxy or relay log: a domain that is not allowed, a private address, a port other than 80 or 443, a direct connection that bypasses the proxy, an external DNS lookup, a request to a provider stored-state endpoint, and a provider-hosted tool. A plain inference request through the relay must succeed with the credential injected.
- The test network uses the subnet `192.0.0.8/29`; its file server and stub provider are reached through the relay's and proxy's extra network.

### F5. Error attribution

Candidates that misbehave in the Evaluation environment, to check Section 10 of the architecture. They run against F3's task pack, so `fixtures/f5-error-attribution/` holds only candidates.

- Crashes the adapter process, exceeds the time limit, exceeds memory, fills its disk quota (only where the backend enforces disk quotas), starts more processes than allowed. Each must end as `failed` with class `case_error`, and the host must stay healthy.
- A simulated host-side failure during a case must lead to the configured number of retries and then `invalid`.
- A simulated host-side failure during the Agent phase must lead to `invalid` immediately.

## 3. Traceability: properties and the tests that demonstrate them

Every security property in `docs/architecture.md` is demonstrated by named tests. This file says which tests support which claim.

A property with no tests is not yet demonstrated. Tests show the behaviors and attacks they exercise, not universal security.

### Security goals

| Goal | Tests |
|---|---|
| G1 Mutual isolation | `tests/fixtures/test_secrecy.py::test_hidden_material_and_contexts_never_enter_an_environment` (no hidden mount, no context in any input, each case gets only its own challenge, the Agent gets only public material); `tests/fixtures/test_fixtures.py::test_f2_repository_build[malicious-hidden-access]`; `tests/unit/test_taskspec.py::test_pack_layout_violations_are_rejected` (a public asset that is a symlink into `hidden/`); `tests/integration/test_candidate.py::test_candidate_faults_fail_capture`, `tests/integration/test_candidate.py::test_capture_replay_and_lookup_round_trip`, `tests/fixtures/test_fixtures.py::test_f1_answer_file` (symlink, oversized, FIFO), `tests/fixtures/test_fixtures.py::test_f2_repository_build[malicious-git-hooks]` and `[malicious-edit-tests]` (excluded paths never enter the candidate), `tests/fixtures/test_fixtures.py::test_expired_agent_time_limit_is_captured_and_evaluated`, qualification probe "no process survives the main process" |
| G2 Verdict integrity | `tests/fixtures/test_fixtures.py::test_f3_generated_file[malicious-forged-observation]`, `tests/fixtures/test_fixtures.py::test_f2_repository_build[malicious-hardcode]` (all-must-pass over hidden cases), `tests/fixtures/test_fixtures.py::test_f1_answer_file[malicious-duplicate-keys]`, `tests/unit/test_oracle.py::test_f1_oracle_plans_and_judges_in_its_own_process` (a verdict claim in the answer is ignored), `tests/unit/test_oracle.py::test_an_oracle_that_raises_or_hangs_fails_the_check`; `tests/adversarial/test_strict_json.py`, `tests/unit/test_evidence.py::test_malformed_responses_never_raise`, `tests/unit/test_evidence.py::test_validation_is_closed_and_strict`, `tests/adversarial/test_capture_stream.py::test_forged_walk_output_is_rejected`, `tests/integration/test_candidate.py::test_collect_reads_only_regular_files_without_following_links`, `tests/unit/test_oracle.py::test_malformed_stored_evidence_is_rejected`, `tests/unit/test_evidence.py::test_json_evidence_leaves_room_for_the_result_record`, `tests/adversarial/test_strict_json.py::test_depth_counts_as_the_encoder_does`, `tests/unit/test_oracle.py::test_an_oracle_that_exhausts_its_memory_fails_the_check`, `tests/unit/test_relay_proxy.py::test_agent_controlled_text_cannot_forge_a_relay_log_line` (records keep agent text as escaped data, architecture Section 11) |
| G3 Test case isolation | qualification probe "clones share no writable state"; `tests/fixtures/test_fixtures.py::test_f2_cases_run_in_parallel_from_one_setup_snapshot`; `tests/fixtures/test_fixtures.py::test_f3_generated_file` (one fresh Evaluation per case) |
| G4 Access control | `tests/fixtures/test_fixtures.py::test_f4_forbidden_routes_fail_and_are_logged` (other domain, private address, other port, direct connections, external DNS, relay stored-state endpoint, hosted tool), `tests/unit/test_relay_proxy.py`, `tests/fixtures/test_model_harness.py::test_a_model_harness_solves_f1_through_the_relay` (Claude Code, with an API key or a subscription token, and Codex reach the model only through the relay, credential injected outside the Agent environment), `tests/unit/test_relay_proxy.py::test_relay_replaces_the_client_bearer_token`, qualification probes "no network by default", "a restricted network reaches only its peers" and "the upstream network reaches only global addresses"; the gap tests in `tests/unit/test_relay_proxy.py`: `::test_a_tls_server_name_other_than_the_connect_host_is_refused`, `::test_trailing_dots_and_case_cannot_widen_a_domain`, `::test_alternate_ipv4_spellings_are_resolved_and_refused`, `::test_ipv6_forms_embedding_a_non_global_ipv4_address_are_refused`, `::test_an_answer_that_changes_after_the_check_is_checked_again`, `::test_relay_paths_differing_in_case_or_encoding_are_refused`, `::test_relay_targets_cannot_reach_another_path`, `::test_relay_strips_method_override_headers`, `::test_relay_rejects_smuggling_before_forwarding`, `::test_relay_forwards_one_request_per_connection`, `::test_relay_never_reveals_its_credential` |

### Isolation backend guarantees

| Guarantee | Tests |
|---|---|
| B1 Declared mounts only; read-only stays read-only; hidden never mounted | `tests/integration/test_qualification.py::test_qualification_probes_pass` (probe "read-only mounts stay read-only") |
| B2 No process survives stop | `tests/integration/test_qualification.py::test_qualification_probes_pass` (probe "no process survives the main process") |
| B3 No shared writable state | `tests/integration/test_qualification.py::test_qualification_probes_pass` (probe "clones share no writable state") |
| B4 Complete destroy | `tests/integration/test_qualification.py::test_qualification_probes_pass` (probe "destroy is complete"); `tests/unit/test_docker_removal.py::test_a_removal_that_never_finishes_is_a_host_error_after_the_deadline`, `tests/unit/test_docker_removal.py::test_any_other_removal_error_is_surfaced_at_once` |
| B5 Network: none by default; restricted networks reach only named peers; upstream networks reach only global addresses | `tests/integration/test_qualification.py::test_qualification_probes_pass` (probes "no network by default", "a restricted network reaches only its peers", "the upstream network reaches only global addresses") |
| B6 Per-environment limits; time, memory and output limits reported | `tests/integration/test_qualification.py::test_qualification_probes_pass` (probes "limits are enforced and reported", "the disk quota is enforced"); `tests/unit/test_docker_arguments.py::test_unrepresentable_timeouts_are_rejected_before_starting` |
| B7 No privilege gain | `tests/integration/test_qualification.py::test_qualification_probes_pass` (probes "no privilege gain" and "the Agent keeps only its five capabilities"); `tests/unit/test_docker_arguments.py::test_arguments_carry_the_hardening_flags`, `::test_no_capability_is_kept_by_default`, `::test_the_agent_keeps_exactly_its_capabilities`, `::test_capabilities_outside_the_agent_set_are_rejected` |
| B8 Images by pinned digest only | `tests/integration/test_qualification.py::test_qualification_probes_pass` (probe "images by pinned digest only"); `tests/unit/test_docker_arguments.py::test_unpinned_images_are_rejected` |

### Errors and verdicts

| Rule (architecture Section 10) | Tests |
|---|---|
| Capture violations fail with class `capture` | `tests/integration/test_candidate.py::test_candidate_faults_fail_capture` (special file, escaping and absolute symlinks, unreadable, over byte and entry bounds) |
| Setup failure fails with class `setup` | `tests/fixtures/test_fixtures.py::test_f2_repository_build[build-failure]` |
| Evaluation-side errors fail with class `case_error` | `tests/fixtures/test_fixtures.py::test_f5_evaluation_errors_are_case_errors` (adapter crash, timeout, memory, processes, disk where quotas are enforced), `tests/integration/test_evaluation.py::test_missing_program_is_a_case_error`, `tests/integration/test_docker_run.py::test_a_cancel_before_the_container_starts_still_stops_it` (a case cancelled before its container starts is stopped, so a candidate that hangs in more cases than run in parallel still ends `failed`) |
| Wrong answers fail with class `oracle` | `tests/unit/test_oracle.py::test_a_diagnostic_too_deep_to_record_fails_the_check`, `tests/unit/test_oracle.py::test_an_oracle_that_exhausts_its_memory_fails_the_check`, `tests/unit/test_oracle.py::test_a_context_too_deep_to_send_fails_the_check`, `tests/fixtures/test_fixtures.py::test_f1_answer_file[wrong]`, `tests/fixtures/test_fixtures.py::test_f2_repository_build[wrong]`, `tests/fixtures/test_fixtures.py::test_f3_generated_file[wrong]`, `tests/fixtures/test_fixtures.py::test_f4_allowed_domain[wrong]` |
| Host error during a case: retries, then `invalid` | `tests/fixtures/test_fixtures.py::test_f5_host_failures_during_cases_are_retried_then_invalid` |
| Host error during the Agent phase or capture: `invalid` immediately | `tests/fixtures/test_fixtures.py::test_f5_host_failure_during_the_agent_phase_is_invalid_at_once`, `tests/integration/test_harness.py::test_preflight_rejects_another_version` |
| Expired Agent time limit: candidate captured and evaluated | `tests/fixtures/test_fixtures.py::test_expired_agent_time_limit_is_captured_and_evaluated` |

### Oracle contract

| Rule (architecture Section 7.5) | Tests or checks |
|---|---|
| `judge` is deterministic | `tests/unit/test_oracle.py::test_static_checks_reject_forbidden_code` (no unseeded `random`, `id` or OS modules; `time` is outside the allowed modules); the worker runs with `PYTHONHASHSEED=0` (`securebench/oracle/process.py`) |
| `judge` has no side effects | `tests/unit/test_oracle.py::test_static_checks_reject_forbidden_code` (no `open`, `os`, `subprocess`, `global`), `tests/unit/test_oracle.py::test_the_oracle_writes_no_bytecode`, `tests/unit/test_oracle.py::test_the_worker_refuses_to_load_a_forbidden_oracle` |
| Evidence is never used as code, path or command | `tests/unit/test_oracle.py::test_static_checks_reject_forbidden_code` (no `eval`, `exec`, `compile`, `pickle`, dunder access) |
| No regular expressions over evidence | `tests/unit/test_oracle.py::test_static_checks_reject_forbidden_code` (`import re` rejected) |

### Candidate model

| Rule (architecture Section 5) | Tests |
|---|---|
| Delta entries: `write`, `dir`, `symlink`, `delete` | `tests/integration/test_candidate.py::test_capture_replay_and_lookup_round_trip`, `tests/integration/test_candidate.py::test_deletion_and_type_change_replay`, `tests/unit/test_candidate_state.py::test_directory_replaced_by_file_deletes_every_descendant`, `tests/unit/test_candidate_state.py::test_executable_bit_alone_is_a_change` |
| Only content, file type and the executable bit survive replay | `tests/integration/test_candidate.py::test_capture_replay_and_lookup_round_trip` (modes 755/644, owner 0) |
| `**/.git` excluded by default; an explicit include is honored | `tests/unit/test_patterns.py::test_git_directories_are_excluded_unless_listed` |
| Unreadable entries fail capture; unreadable output files fail the case | `tests/integration/test_candidate.py::test_candidate_faults_fail_capture` (mode 000 file and directory), `tests/unit/test_candidate_state.py::test_utility_rejects_special_files_and_unreadable_files` |
| Replay refuses a mismatched baseline | `tests/integration/test_candidate.py::test_replay_refuses_a_candidate_from_another_baseline`, `tests/unit/test_candidate_state.py::test_stored_candidates_are_rechecked_against_the_current_task` |
| Host validation rejects out-of-scope paths from a compromised capture | `tests/adversarial/test_capture_stream.py::test_forged_walk_output_is_rejected`, `tests/adversarial/test_capture_stream.py::test_excluded_paths_are_dropped_whatever_the_utility_sent` |
